import hashlib
import psutil
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.db import get_db, AuditLog, User, compute_audit_hash
from ..core.auth import get_current_user
from ..core.config import settings
from ..core import security_monitor
from ..agent.model_router import MODEL_REGISTRY, available_ram_gb
from ..agent.llm_client import list_local_models

router = APIRouter(tags=["misc"])

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/version")
def version():
    return {"version": "0.2.0-mvp"}

@router.get("/ready")
def ready_check(db: Session = Depends(get_db)):
    try:
        # Check DB
        db.execute("SELECT 1")
        # Check Chroma
        from ..tools.rag_store import _collection
        if not _collection:
            raise Exception("Chroma collection not initialized")
        _collection.count()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(503, f"Service not fully ready: {e}")


@router.get("/aliases")
def get_aliases(db: Session = Depends(get_db)):
    from ..core.db import ParameterAlias
    aliases = db.query(ParameterAlias).all()
    return [{"id": a.id, "canonical_name": a.canonical_name, "alias": a.alias} for a in aliases]


from pydantic import BaseModel
class AliasCreate(BaseModel):
    canonical_name: str
    alias: str


@router.post("/aliases")
def create_alias(payload: AliasCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "ADMIN":
        raise HTTPException(403, "Only ADMIN can manage aliases")
    from ..core.db import ParameterAlias, create_audit_log
    new_alias = ParameterAlias(canonical_name=payload.canonical_name.lower().strip(), alias=payload.alias.lower().strip())
    db.add(new_alias)
    db.commit()
    create_audit_log(db, user_id=user.id, action="CREATE_ALIAS", detail=f"Added alias '{payload.alias}' for '{payload.canonical_name}'")
    return {"id": new_alias.id, "canonical_name": new_alias.canonical_name, "alias": new_alias.alias}


@router.delete("/aliases/{alias_id}")
def delete_alias(alias_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "ADMIN":
        raise HTTPException(403, "Only ADMIN can manage aliases")
    from ..core.db import ParameterAlias, create_audit_log
    alias = db.query(ParameterAlias).filter(ParameterAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(404, "Alias not found")
    db.delete(alias)
    db.commit()
    create_audit_log(db, user_id=user.id, action="DELETE_ALIAS", detail=f"Deleted alias '{alias.alias}' for '{alias.canonical_name}'")
    return {"status": "ok"}


@router.get("/models")
def get_models():
    installed = list_local_models()
    return {
        "registry": MODEL_REGISTRY,
        "installed_locally": installed,
        "available_ram_gb": available_ram_gb(),
    }


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    from ..core.db import Task
    tasks = db.query(Task).all()
    total_tasks = len(tasks)
    
    status_counts = {}
    approval_counts = {}
    
    total_processing_time = 0
    completed_tasks_with_time = 0
    
    for t in tasks:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
        approval_counts[t.approval_status] = approval_counts.get(t.approval_status, 0) + 1
        
        if t.completed_at and t.created_at:
            total_processing_time += (t.completed_at - t.created_at).total_seconds()
            completed_tasks_with_time += 1
            
    avg_processing_time = total_processing_time / completed_tasks_with_time if completed_tasks_with_time > 0 else 0
    
    return {
        "total_tasks": total_tasks,
        "status_counts": status_counts,
        "approval_counts": approval_counts,
        "avg_processing_time_seconds": avg_processing_time
    }


@router.get("/security/status")
def security_status():
    events = security_monitor.get_events()
    counters = security_monitor.get_counters()
    return {
        "outbound_network_enabled": settings.OUTBOUND_NETWORK,
        "blocked_attempts": counters["blocked_attempts"],
        "external_calls_succeeded": counters["external_calls_succeeded"],
        "total_socket_events": len(events),
        "recent_events": events[-30:],
        "cpu_percent": psutil.cpu_percent(),
        "ram_available_gb": available_ram_gb(),
        "air_gapped_mode": not settings.OUTBOUND_NETWORK,
    }


@router.post("/security/selftest")
def security_selftest():
    """
    Attempt a connection to 8.8.8.8:443 to prove the network guard blocks it.
    Increments blocked_attempts; external_calls_succeeded must stay 0.
    """
    result = security_monitor.selftest()
    counters = security_monitor.get_counters()
    return {
        **result,
        "blocked_attempts": counters["blocked_attempts"],
        "external_calls_succeeded": counters["external_calls_succeeded"],
    }


@router.get("/audit/project/{project_id}")
def audit_logs(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logs = db.query(AuditLog).filter(AuditLog.project_id == project_id).order_by(AuditLog.timestamp.desc()).limit(200).all()
    return [{
        "id": l.id, "user_id": l.user_id, "action": l.action, "detail": l.detail,
        "timestamp": l.timestamp.isoformat(),
        "entry_hash": l.entry_hash or "",
        "prev_hash": l.prev_hash or "",
    } for l in logs]


@router.get("/audit/all")
def all_audit_logs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(200).all()
    return [{
        "id": l.id, "user_id": l.user_id, "action": l.action, "detail": l.detail,
        "timestamp": l.timestamp.isoformat(),
        "entry_hash": l.entry_hash or "",
        "prev_hash": l.prev_hash or "",
    } for l in logs]


@router.get("/audit/verify")
def verify_audit_chain(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Verify the tamper-evident audit log hash chain.
    Returns OK if the chain is intact, or the first broken entry.
    """
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.asc()).all()
    if not logs:
        return {"status": "OK", "detail": "No audit log entries to verify."}

    prev_hash = "GENESIS"
    for i, entry in enumerate(logs):
        if not entry.entry_hash:
            return {
                "status": "TAMPERED",
                "broken_entry_id": entry.id,
                "broken_index": i,
                "detail": f"Entry #{i} is missing entry_hash (tampering detected)."
            }

        expected_hash = compute_audit_hash(
            entry.prev_hash or "GENESIS",
            entry.user_id or "",
            entry.action or "",
            entry.detail or "",
            entry.timestamp.isoformat() if entry.timestamp else "",
        )

        if entry.entry_hash != expected_hash:
            return {
                "status": "TAMPERED",
                "broken_entry_id": entry.id,
                "broken_index": i,
                "detail": f"Entry #{i} hash mismatch. Expected {expected_hash[:16]}..., got {entry.entry_hash[:16]}...",
            }

        if entry.prev_hash and entry.prev_hash != prev_hash and prev_hash != "GENESIS":
            return {
                "status": "CHAIN_BROKEN",
                "broken_entry_id": entry.id,
                "broken_index": i,
                "detail": f"Entry #{i} prev_hash does not match previous entry's hash.",
            }

        prev_hash = entry.entry_hash

    return {"status": "OK", "detail": f"All {len(logs)} audit log entries verified. Chain is intact."}
