import datetime
import uuid
import hashlib
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Integer, ForeignKey, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from .config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def gen_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_id)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="USER")  # ADMIN | USER | REVIEWER
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    owner_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ProjectMember(Base):
    __tablename__ = "project_members"
    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"))
    user_id = Column(String, ForeignKey("users.id"))
    role = Column(String, default="USER")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=gen_id)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    file_type = Column(String)
    project_id = Column(String, ForeignKey("projects.id"))
    uploader_id = Column(String, ForeignKey("users.id"))
    confidentiality = Column(String, default="Internal")
    doc_role = Column(String, default="OTHER") # SOP | INSPECTION_REPORT | OTHER
    version = Column(String, default="1.0")
    status = Column(String, default="ACTIVE") # ACTIVE | SUPERSEDED
    effective_date = Column(DateTime, default=datetime.datetime.utcnow)
    processing_status = Column(String, default="PENDING")  # PENDING|PROCESSING|DONE|FAILED
    checksum = Column(String, default="")
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"))
    user_id = Column(String, ForeignKey("users.id"))
    input_text = Column(Text)
    status = Column(String, default="RECEIVED")
    selected_model = Column(String, default="")
    model_reason = Column(String, default="")
    plan_json = Column(Text, default="[]")
    steps_json = Column(Text, default="[]")  # execution timeline
    sources_json = Column(Text, default="[]")
    verification_json = Column(Text, default="{}")
    compliance_json = Column(Text, default="[]")
    result_text = Column(Text, default="")
    artifact_id = Column(String, default="")
    requires_approval = Column(Boolean, default=False)
    approval_status = Column(String, default="NONE")  # NONE|PENDING|APPROVED|REJECTED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class Artifact(Base):
    __tablename__ = "artifacts"
    id = Column(String, primary_key=True, default=gen_id)
    task_id = Column(String, ForeignKey("tasks.id"))
    filename = Column(String)
    filepath = Column(String)
    kind = Column(String, default="docx")
    quality_status = Column(String, default="UNVERIFIED")  # PASS|FAIL|UNVERIFIED
    sha256 = Column(String, default="")  # SHA-256 hash of artifact file
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, default="")
    action = Column(String)
    detail = Column(Text, default="")
    project_id = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    # Tamper-evident hash chain
    prev_hash = Column(String, default="")
    entry_hash = Column(String, default="")


class SecurityEvent(Base):
    __tablename__ = "security_events"
    id = Column(String, primary_key=True, default=gen_id)
    event_type = Column(String)  # OUTBOUND_ATTEMPT | BLOCKED | LOCAL | INFO
    detail = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class AssetHistory(Base):
    __tablename__ = "asset_history"
    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"))
    asset_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    thickness = Column(Float, nullable=False)


class ParameterAlias(Base):
    __tablename__ = "parameter_aliases"
    id = Column(String, primary_key=True, default=gen_id)
    canonical_name = Column(String, nullable=False)
    alias = Column(String, nullable=False)


def init_db():
    import alembic.config
    import alembic.command
    import os
    
    # Run Alembic migrations programmatically
    alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "alembic.ini")
    
    if os.path.exists(alembic_ini_path):
        alembic_cfg = alembic.config.Config(alembic_ini_path)
        # Point to the correct script location
        script_location = os.path.join(os.path.dirname(alembic_ini_path), "alembic")
        alembic_cfg.set_main_option("script_location", script_location)
        try:
            alembic.command.upgrade(alembic_cfg, "head")
        except Exception as e:
            import logging
            logging.getLogger("trustforge.db").error(f"Alembic migration failed: {e}")
            raise
    else:
        # Fallback if alembic.ini is completely missing (should not happen in normal deployments)
        Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def compute_audit_hash(prev_hash: str, user_id: str, action: str, detail: str, timestamp: str) -> str:
    """Compute SHA-256 hash for audit chain integrity."""
    data = f"{prev_hash}|{user_id}|{action}|{detail}|{timestamp}"
    return hashlib.sha256(data.encode()).hexdigest()


def create_audit_log(db, user_id: str, action: str, detail: str = "", project_id: str = ""):
    """Create an audit log entry with tamper-evident hash chain."""
    # Get the hash of the most recent entry
    last_entry = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()
    prev_hash = last_entry.entry_hash if last_entry and last_entry.entry_hash else "GENESIS"

    timestamp = datetime.datetime.utcnow()
    entry_hash = compute_audit_hash(prev_hash, user_id, action, detail, timestamp.isoformat())

    log = AuditLog(
        user_id=user_id,
        action=action,
        detail=detail,
        project_id=project_id,
        timestamp=timestamp,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )
    db.add(log)
    db.commit()
    return log
