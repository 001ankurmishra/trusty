from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.db import get_db, Project, ProjectMember, User, AuditLog, create_audit_log
from ..core.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectIn(BaseModel):
    name: str
    description: str = ""


@router.post("")
def create_project(payload: ProjectIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    proj = Project(name=payload.name, description=payload.description, owner_id=user.id)
    db.add(proj)
    db.commit()
    # Auto-add creator as project member (OWNER role)
    member = ProjectMember(project_id=proj.id, user_id=user.id, role="OWNER")
    db.add(member)
    db.commit()
    create_audit_log(db, user_id=user.id, action="CREATE_PROJECT", detail=proj.name, project_id=proj.id)
    return {"id": proj.id, "name": proj.name, "description": proj.description}


@router.get("")
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List projects. ADMIN sees all; others see only projects they are a member of."""
    if user.role == "ADMIN":
        projects = db.query(Project).all()
    else:
        member_project_ids = [
            m.project_id for m in db.query(ProjectMember).filter(ProjectMember.user_id == user.id).all()
        ]
        projects = db.query(Project).filter(Project.id.in_(member_project_ids)).all() if member_project_ids else []
    return [{"id": p.id, "name": p.name, "description": p.description} for p in projects]


class AddMemberIn(BaseModel):
    user_id: str
    role: str = "USER"


@router.post("/{project_id}/members")
def add_member(
    project_id: str,
    payload: AddMemberIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a user to a project. Only project OWNER or ADMIN can add members."""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    # Check authorization
    if user.role != "ADMIN":
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.role == "OWNER",
        ).first()
        if not member:
            from fastapi import HTTPException
            raise HTTPException(403, "Only the project owner or ADMIN can add members")
    # Prevent duplicates
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == payload.user_id,
    ).first()
    if existing:
        return {"detail": "User is already a member"}
    new_member = ProjectMember(project_id=project_id, user_id=payload.user_id, role=payload.role)
    db.add(new_member)
    db.commit()
    create_audit_log(db, user_id=user.id, action="ADD_MEMBER", detail=payload.user_id, project_id=project_id)
    return {"detail": "Member added"}
