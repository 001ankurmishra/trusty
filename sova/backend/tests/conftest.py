import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.db import Base, get_db, User, Project, ProjectMember
from app.core.auth import hash_password
from app.core.security_monitor import install_network_guard

# Ensure network guard is installed for tests
install_network_guard()

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    import alembic.config
    import alembic.command
    import os
    
    # Remove test DB if exists
    if os.path.exists("./test.db"):
        os.remove("./test.db")
        
    alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic.ini")
    alembic_cfg = alembic.config.Config(alembic_ini_path)
    script_location = os.path.join(os.path.dirname(alembic_ini_path), "alembic")
    
    alembic_cfg.set_main_option("script_location", script_location)
    alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
    alembic.command.upgrade(alembic_cfg, "head")
        
    db = TestingSessionLocal()
    
    # Create test users
    admin = User(id="admin_id", username="admin", password_hash=hash_password("admin123"), role="ADMIN")
    user1 = User(id="user1_id", username="user1", password_hash=hash_password("user123"), role="USER")
    user2 = User(id="user2_id", username="user2", password_hash=hash_password("user223"), role="USER")
    reviewer = User(id="reviewer_id", username="reviewer", password_hash=hash_password("reviewer123"), role="REVIEWER")
    
    db.add(admin)
    db.add(user1)
    db.add(user2)
    db.add(reviewer)
    db.commit()

    # Create test project
    project = Project(id="proj1", name="Test Project", owner_id="user1_id")
    db.add(project)
    db.commit()
    
    # Add members
    db.add(ProjectMember(project_id="proj1", user_id="user1_id", role="OWNER"))
    db.add(ProjectMember(project_id="proj1", user_id="reviewer_id", role="REVIEWER"))
    db.commit()

    yield
    
    db.close()
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

import app.core.db as core_db
core_db.SessionLocal = TestingSessionLocal
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def auth_headers(client):
    def _get_headers(username, password):
        response = client.post("/auth/login", data={"username": username, "password": password})
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _get_headers
