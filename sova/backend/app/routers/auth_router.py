import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.db import get_db, User, AuditLog, create_audit_log
from ..core.auth import hash_password, verify_password, create_access_token, get_current_user, require_role
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterIn(BaseModel):
    username: str
    password: str
    role: str = "USER"

@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, "Username already exists")
    if len(payload.password) < settings.MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters")
    user = User(username=payload.username, password_hash=hash_password(payload.password), role="USER")
    db.add(user)
    db.commit()
    create_audit_log(db, user_id=user.id, action="REGISTER", detail=f"user {user.username} created as USER")
    return {"id": user.id, "username": user.username, "role": user.role}

# Simple in-memory rate limiting: username -> {"count": int, "locked_until": float}
FAILED_ATTEMPTS = {}
MAX_ATTEMPTS = 5
LOCKOUT_DURATION_SEC = 300  # 5 minutes

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    now = time.time()
    
    # Check rate limit
    record = FAILED_ATTEMPTS.get(form.username, {"count": 0, "locked_until": 0})
    if record["locked_until"] > now:
        raise HTTPException(429, "Too many failed attempts. Try again later.")
    
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        record["count"] += 1
        if record["count"] >= MAX_ATTEMPTS:
            record["locked_until"] = now + LOCKOUT_DURATION_SEC
        FAILED_ATTEMPTS[form.username] = record
        create_audit_log(db, user_id="SYSTEM", action="LOGIN_FAILED", detail=f"Failed login attempt for username {form.username}")
        raise HTTPException(401, "Invalid username or password")
    
    # Success -> reset limits
    FAILED_ATTEMPTS.pop(form.username, None)
    
    token = create_access_token({"sub": user.id, "role": user.role})
    create_audit_log(db, user_id=user.id, action="LOGIN", detail="login success")
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
    create_audit_log(
        db,
        user_id=admin.id,
        action="ROLE_CHANGE",
        detail=f"Changed {target.username} from {old_role} to {payload.role}",
    )
    return {"id": target.id, "username": target.username, "role": target.role}

class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str

@router.post("/change-password")
def change_password(
    payload: ChangePasswordIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(401, "Invalid old password")
    if len(payload.new_password) < settings.MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters")
    
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    create_audit_log(db, user_id=user.id, action="PASSWORD_CHANGE", detail="User changed password")
    return {"status": "success"}
