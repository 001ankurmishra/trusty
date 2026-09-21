from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.db import get_db, User, AuditLog
from ..core.auth import hash_password, verify_password, create_access_token, get_current_user, require_role
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str
    password: str
    role: str = "USER"  # ignored for public registration — always USER


@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, "Username already exists")
    if len(payload.password) < settings.MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters")
    # SECURITY: Public registration always creates USER role.
    # Role changes only through the ADMIN-only endpoint below.
    user = User(username=payload.username, password_hash=hash_password(payload.password), role="USER")
    db.add(user)
    db.commit()
    db.add(AuditLog(user_id=user.id, action="REGISTER", detail=f"user {user.username} created as USER"))
    db.commit()
    return {"id": user.id, "username": user.username, "role": user.role}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    token = create_access_token({"sub": user.id, "role": user.role})
    db.add(AuditLog(user_id=user.id, action="LOGIN", detail="login success"))
    db.commit()
    return {"access_token": token, "token_type": "bearer", "role": user.role, "username": user.username}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}


class RoleChangeIn(BaseModel):
    role: str


@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    payload: RoleChangeIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("ADMIN")),
):
    """ADMIN-only: change a user's role."""
    if payload.role not in ("ADMIN", "USER", "REVIEWER"):
        raise HTTPException(400, "Invalid role. Must be ADMIN, USER, or REVIEWER.")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    old_role = target.role
    target.role = payload.role
    db.commit()
    db.add(AuditLog(
        user_id=admin.id,
        action="ROLE_CHANGE",
        detail=f"Changed {target.username} from {old_role} to {payload.role}",
    ))
    db.commit()
    return {"id": target.id, "username": target.username, "role": target.role}
