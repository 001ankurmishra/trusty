"""Run once: python bootstrap_admin.py  -> creates admin/admin123"""
from app.core.db import init_db, SessionLocal, User
from app.core.auth import hash_password

init_db()
db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    db.add(User(username="admin", password_hash=hash_password("admin123"), role="ADMIN"))
    db.add(User(username="reviewer", password_hash=hash_password("reviewer123"), role="REVIEWER"))
    db.commit()
    print("Created: admin/admin123 (ADMIN), reviewer/reviewer123 (REVIEWER)")
else:
    print("Admin user already exists.")
db.close()
