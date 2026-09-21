import json
import hashlib
import datetime
import threading
import concurrent.futures
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..core.db import get_db, Task, Artifact, User, AuditLog, Project, ProjectMember, create_audit_log
from ..core.auth import get_current_user, require_role
from ..core import security_monitor
from ..agent.orchestrator import run_task
from ..tools import docgen

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Thread pool for background task execution
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="trustforge-task")


class TaskIn(BaseModel):
    project_id: str
    input_text: str
    has_image: bool = False


def _check_project_access(project_id: str, user: User, db: Session):
    """Enforce project membership. ADMIN sees all."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    if user.role == "ADMIN":
        return project
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(403, "You are not a member of this project")
    return project


def _run_task_background(task_id: str, input_text: str, project_id: str,
                          has_image: bool, user_id: str, user_role: str):
    """Run the agent in a background thread and update the DB with results."""
    from ..core.db import SessionLocal

    def step_callback(steps):
        """Persist steps to DB in real-time for live timeline polling."""
        try:
            db = SessionLocal()
            try:
                t = db.query(Task).filter(Task.id == task_id).first()
                if t:
                    t.steps_json = json.dumps(steps)
                    db.commit()
            finally:
                db.close()
        except Exception:
            pass

    try:
        result = run_task(
            input_text, project_id,
            has_image=has_image,
            user_role=user_role,
            step_callback=step_callback,
        )
    except Exception as e:
        result = {
            "steps": [{"step": "Task failed", "status": "FAILED", "detail": str(e),
                       "timestamp": datetime.datetime.utcnow().isoformat()}],
            "route_info": {},
            "sources": [],
            "result_text": f"Task failed: {e}",
            "verification": {"ran": False, "error": str(e)},
            "requires_approval": False,
            "artifact_path": None,
            "artifact_name": None,
            "compliance_table": [],
            "error": str(e),
        }

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        is_error = result.get("error") is not None
        if is_error:
            task.status = "FAILED"
        elif result["requires_approval"]:
            task.status = "AWAITING_APPROVAL"
        else:
            task.status = "COMPLETED"

        task.selected_model = result.get("route_info", {}).get("selected_model", "")
        task.model_reason = result.get("route_info", {}).get("reason", "")
        task.steps_json = json.dumps(result["steps"])
        task.sources_json = json.dumps(result["sources"])
        task.verification_json = json.dumps(result["verification"])
        task.compliance_json = json.dumps(result.get("compliance_table", []))
        task.result_text = result["result_text"]
        task.requires_approval = result["requires_approval"]
        task.approval_status = "PENDING" if result["requires_approval"] else "NONE"
        task.completed_at = datetime.datetime.utcnow()

        if result.get("artifact_path") and not is_error:
            # Compute SHA-256 of the artifact
            sha256 = ""
            try:
                with open(result["artifact_path"], "rb") as f:
                    sha256 = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                pass

            artifact = Artifact(
                task_id=task.id, filename=result["artifact_name"], filepath=result["artifact_path"],
                kind="docx",
                quality_status=result["verification"].get("deliverable_quality_check", "UNVERIFIED"),
                sha256=sha256,
            )
            db.add(artifact)
            db.commit()
            task.artifact_id = artifact.id

        db.commit()
        create_audit_log(db, user_id=user_id, action="RUN_TASK", detail=input_text[:200], project_id=project_id)
    finally:
        db.close()


@router.post("")
def create_and_run_task(payload: TaskIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _check_project_access(payload.project_id, user, db)

    task = Task(project_id=payload.project_id, user_id=user.id, input_text=payload.input_text, status="RUNNING")
    db.add(task)
    db.commit()
    task_id = task.id

    # Launch in background thread so the HTTP response returns immediately
    _executor.submit(
        _run_task_background,
        task_id, payload.input_text, payload.project_id,
        payload.has_image, user.id, user.role,
    )

    return _serialize_task(task)


def _serialize_task(task: Task):
    return {
        "id": task.id, "status": task.status, "input_text": task.input_text,
        "selected_model": task.selected_model, "model_reason": task.model_reason,
        "steps": json.loads(task.steps_json), "sources": json.loads(task.sources_json),
        "verification": json.loads(task.verification_json), 
        "compliance_table": json.loads(task.compliance_json) if task.compliance_json else [],
        "result_text": task.result_text,
        "requires_approval": task.requires_approval, "approval_status": task.approval_status,
        "artifact_id": task.artifact_id, "created_at": task.created_at.isoformat(),
    }


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    _check_project_access(task.project_id, user, db)
    return _serialize_task(task)


@router.get("/project/{project_id}")
def list_tasks(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _check_project_access(project_id, user, db)
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).all()
    return [_serialize_task(t) for t in tasks]


from ..core.auth import get_current_user, require_role, verify_password

# ... skipped to ApprovalIn

@router.get("/inbox")
def list_inbox_tasks(db: Session = Depends(get_db), user: User = Depends(require_role("REVIEWER", "ADMIN"))):
    # Only AWAITING_APPROVAL tasks for projects the user has access to
    if user.role == "ADMIN":
        tasks = db.query(Task).filter(Task.approval_status == "PENDING").order_by(Task.created_at.desc()).all()
    else:
        # User is REVIEWER - they only see tasks from projects they belong to
        tasks = db.query(Task).join(ProjectMember, Task.project_id == ProjectMember.project_id)\
            .filter(ProjectMember.user_id == user.id, Task.approval_status == "PENDING")\
            .order_by(Task.created_at.desc()).all()
            
    # Filter out tasks created by the user themselves unless ADMIN
    if user.role != "ADMIN":
        tasks = [t for t in tasks if t.user_id != user.id]
        
    return [_serialize_task(t) for t in tasks]

class ApprovalIn(BaseModel):
    comment: str = ""
    password: str = ""


@router.post("/{task_id}/approve")
def approve_task(
    task_id: str,
    payload: ApprovalIn = ApprovalIn(),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("REVIEWER", "ADMIN")),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    _check_project_access(task.project_id, user, db)
    if not task.requires_approval:
        raise HTTPException(400, "This task does not require approval")
    if task.approval_status != "PENDING":
        raise HTTPException(400, f"Task approval status is {task.approval_status}, not PENDING")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid password (e-signature failed)")

    # Four-eyes: approver must be different from creator (except ADMIN override)
    is_admin_override = (user.id == task.user_id and user.role == "ADMIN")
    if user.id == task.user_id and not is_admin_override:
        raise HTTPException(403, "Four-eyes principle: you cannot approve your own task. A different reviewer is required.")

    task.approval_status = "APPROVED"
    task.status = "COMPLETED"
    steps = json.loads(task.steps_json)
    steps.append({
        "step": "Human review completed",
        "status": "DONE",
        "detail": f"Approved by {user.username}" + (f" (comment: {payload.comment})" if payload.comment else "")
                  + (" [ADMIN OVERRIDE]" if is_admin_override else ""),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    task.steps_json = json.dumps(steps)
    db.commit()

    # Regenerate DOCX with approval info
    artifact = db.query(Artifact).filter(Artifact.task_id == task_id).first()
    if artifact:
        try:
            sources = json.loads(task.sources_json)
            verification = json.loads(task.verification_json)
            filepath, filename = docgen.generate_approval_note(
                task_id=task.id,
                subject=task.input_text[:200],
                findings=task.result_text,
                sources=sources,
                calculations="",
                recommendations="",
                verification=verification,
                compliance_table=json.loads(task.compliance_json) if task.compliance_json else [],
                reviewer_name=user.username,
                decision="APPROVED",
                decision_timestamp=datetime.datetime.utcnow().isoformat(),
                comments=payload.comment,
            )
            # Update artifact with new file and hash
            sha256 = ""
            try:
                with open(filepath, "rb") as f:
                    sha256 = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                pass
            artifact.filepath = filepath
            artifact.filename = filename
            artifact.sha256 = sha256
            db.commit()
        except Exception:
            pass  # if regeneration fails, keep old artifact

    action = "APPROVE_TASK_OVERRIDE" if is_admin_override else "APPROVE_TASK"
    create_audit_log(
        db,
        user_id=user.id, action=action,
        detail=f"{task_id}" + (f" comment: {payload.comment}" if payload.comment else ""),
        project_id=task.project_id,
    )
    return _serialize_task(task)


@router.post("/{task_id}/reject")
def reject_task(
    task_id: str,
    payload: ApprovalIn = ApprovalIn(),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("REVIEWER", "ADMIN")),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    _check_project_access(task.project_id, user, db)
    if not task.requires_approval:
        raise HTTPException(400, "This task does not require approval")
    if task.approval_status != "PENDING":
        raise HTTPException(400, f"Task approval status is {task.approval_status}, not PENDING")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid password (e-signature failed)")

    # Four-eyes for reject too
    if user.id == task.user_id and user.role != "ADMIN":
        raise HTTPException(403, "Four-eyes principle: you cannot reject your own task.")

    task.approval_status = "REJECTED"
    task.status = "REJECTED"
    steps = json.loads(task.steps_json)
    steps.append({
        "step": "Human review completed",
        "status": "FAILED",
        "detail": f"Rejected by {user.username}" + (f" (comment: {payload.comment})" if payload.comment else ""),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    task.steps_json = json.dumps(steps)
    db.commit()
    create_audit_log(
        db,
        user_id=user.id, action="REJECT_TASK",
        detail=f"{task_id}" + (f" comment: {payload.comment}" if payload.comment else ""),
        project_id=task.project_id,
    )
    return _serialize_task(task)


@router.get("/{task_id}/receipt")
def work_receipt(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """FR-22 AI Work Receipt — with REAL security counter values."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    _check_project_access(task.project_id, user, db)

    # Get real security counters
    counters = security_monitor.get_counters()

    # Get artifact hash if available
    artifact_sha256 = None
    artifact = db.query(Artifact).filter(Artifact.task_id == task_id).first()
    if artifact:
        artifact_sha256 = artifact.sha256

    return {
        "task": task.input_text,
        "task_id": task.id,
        "models_used": [task.selected_model],
        "documents_used": [s["filename"] for s in json.loads(task.sources_json)],
        "tools_used": [s["step"] for s in json.loads(task.steps_json) if "Tool" in s["step"]],
        "verification_status": json.loads(task.verification_json),
        "blocked_attempts": counters["blocked_attempts"],
        "external_calls_succeeded": counters["external_calls_succeeded"],
        "human_review_status": task.approval_status,
        "artifact_sha256": artifact_sha256,
        "completion_timestamp": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.get("/artifact/{artifact_id}/download")
def download_artifact(artifact_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(404, "Artifact not found")

    # Check task approval status — block download if PENDING or REJECTED
    task = db.query(Task).filter(Task.id == artifact.task_id).first()
    if task:
        _check_project_access(task.project_id, user, db)
        if task.requires_approval:
            if task.approval_status == "PENDING":
                raise HTTPException(403, "Artifact download blocked: task requires approval and is still PENDING.")
            if task.approval_status == "REJECTED":
                raise HTTPException(403, "Artifact download blocked: task was REJECTED.")

    return FileResponse(artifact.filepath, filename=artifact.filename)
