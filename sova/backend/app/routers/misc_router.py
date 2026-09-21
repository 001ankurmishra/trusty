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


@router.get("/models")
def get_models():
    installed = list_local_models()
    return {
        "registry": MODEL_REGISTRY,
        "installed_locally": installed,
        "available_ram_gb": available_ram_gb(),
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
        # Skip entries without hash (pre-migration entries)
        if not entry.entry_hash:
            continue

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
