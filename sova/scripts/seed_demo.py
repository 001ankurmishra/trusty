#!/usr/bin/env python3
"""
Seed data for the TrustForge demo.
Creates a sample project, uploads a dummy SOP and Inspection Report (DOCX),
and ensures the database is ready for a demo.
"""
import os
import sys
import datetime
from docx import Document

# Add backend directory to path so we can import app modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "backend")
sys.path.append(BACKEND_DIR)

from app.core.db import SessionLocal, User, Project, ProjectMember, AuditLog
from app.routers.documents_router import upload_document
from fastapi import UploadFile
import io
import asyncio

def create_sample_docx(filename, content):
    doc = Document()
    doc.add_heading(filename.replace(".docx", ""), 0)
    for line in content.split('\n'):
        if line.strip():
            doc.add_paragraph(line.strip())
    doc.save(filename)
    return filename

SOP_CONTENT = """
Standard Operating Procedure: Pressure Vessel Safety
Document ID: SOP-PV-004
Confidentiality: Internal

1. Scope
This SOP covers the safety limits for the industrial pressure vessels in Sector 7.

2. Safety Limits
- Maximum Allowable Working Pressure (MAWP): 150 PSI
- Maximum Operating Temperature: 85°C
- Minimum Wall Thickness: 12.5 mm

3. Inspection Requirements
Inspections must be carried out annually. Any vessel exceeding the MAWP or operating temperature, or falling below the minimum wall thickness, must be taken offline immediately for maintenance.
"""

REPORT_CONTENT = """
Inspection Report: Vessel V-102
Date: 2024-10-15
Inspector: Jane Doe
Confidentiality: Confidential

1. Visual Inspection
The vessel shows normal wear. No visible cracks or corrosion on the exterior.

2. Measurements
- Operating Pressure: 165 PSI
- Current Temperature: 82°C
- Measured Wall Thickness: 13.1 mm

3. Notes
The pressure gauge appears to be reading higher than normal. Recommend a calibration check on the gauge, and an immediate review of the pressure settings to ensure compliance with safety standards.
"""

async def main():
    print("Seeding TrustForge demo data...")
    db = SessionLocal()
    
    # 1. Ensure admin user exists
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        from app.core.auth import hash_password
        admin = User(username="admin", password_hash=hash_password("admin123"), role="ADMIN")
        db.add(admin)
        db.commit()
        print("Created admin user.")
        
    # 2. Create a demo project
    proj_name = "Sector 7 Safety Review"
    project = db.query(Project).filter(Project.name == proj_name).first()
    if not project:
        project = Project(name=proj_name, description="Annual safety review for Sector 7 pressure vessels.", owner_id=admin.id)
        db.add(project)
        db.commit()
        
        member = ProjectMember(project_id=project.id, user_id=admin.id, role="OWNER")
        db.add(member)
        db.add(AuditLog(user_id=admin.id, action="CREATE_PROJECT", detail=project.name, project_id=project.id))
        db.commit()
        print(f"Created project: {proj_name}")
    else:
        print(f"Project '{proj_name}' already exists.")

    # 3. Create sample docs locally
    sop_file = create_sample_docx("SOP_Pressure_Vessel.docx", SOP_CONTENT)
    report_file = create_sample_docx("Inspection_V-102.docx", REPORT_CONTENT)
    
    print("Created sample DOCX files locally.")

    # Note: We won't try to mock the FastAPI UploadFile flow here because it's complex to mock
    # the entire request context. We'll instruct the user to upload these via the UI for the demo.
    
    print("\n✅ Database seeded successfully!")
    print("\nTo complete the demo setup:")
    print("1. Log in to the UI as 'admin' / 'admin123'")
    print("2. Navigate to the 'Sector 7 Safety Review' project")
    print("3. Upload the two files created in this directory:")
    print(f"   - {os.path.abspath(sop_file)}")
    print(f"   - {os.path.abspath(report_file)}")
    print("4. Go to the Workbench and run:")
    print("   'Analyze the inspection report for V-102 against our SOP limits and prepare an approval note.'")

if __name__ == "__main__":
    asyncio.run(main())
