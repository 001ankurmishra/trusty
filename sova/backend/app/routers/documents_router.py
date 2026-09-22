import os
import uuid
import hashlib
import base64
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from ..core.db import get_db, Document, User, AuditLog, ProjectMember, Project, create_audit_log
from ..core.auth import get_current_user
from ..core.config import settings
from ..tools import doc_parser, rag_store

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXT = {"pdf", "docx", "xlsx", "png", "jpg", "jpeg", "txt", "py"}
IMAGE_EXT = {"png", "jpg", "jpeg"}

# Basic content-type validation
EXT_CONTENT_TYPES = {
    "pdf": ["application/pdf"],
    "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    "png": ["image/png"],
    "jpg": ["image/jpeg"],
    "jpeg": ["image/jpeg"],
    "txt": ["text/plain", "application/octet-stream"],
    "py": ["text/plain", "text/x-python", "application/octet-stream"],
}


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


@router.post("/upload")
async def upload_document(
    project_id: str = Form(...),
    confidentiality: str = Form("Internal"),
    doc_role: str = Form("OTHER"),
    version: str = Form("1.0"),
    status: str = Form("ACTIVE"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _check_project_access(project_id, user, db)

    if not file.filename or not file.filename.strip():
        raise HTTPException(400, "Empty filename")

    # Sanitize filename: take only the basename and prefix with UUID
    safe_name = os.path.basename(file.filename).strip()
    if not safe_name:
        raise HTTPException(400, "Invalid filename")

    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXT))}")

    # Content-type validation (basic)
    if file.content_type:
        allowed_types = EXT_CONTENT_TYPES.get(ext, [])
        if allowed_types and file.content_type not in allowed_types and file.content_type != "application/octet-stream":
            raise HTTPException(400, f"Content type '{file.content_type}' does not match extension '.{ext}'")

    # Read content FIRST, check size BEFORE writing to disk
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "File is empty")
    if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")

    # UUID-prefixed filename prevents collisions and path traversal
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    project_dir = os.path.join(settings.UPLOAD_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    filepath = os.path.join(project_dir, unique_name)

    with open(filepath, "wb") as f:
        f.write(content)

    checksum = hashlib.sha256(content).hexdigest()

    doc = Document(
        filename=safe_name, filepath=filepath, file_type=ext, project_id=project_id,
        uploader_id=user.id, confidentiality=confidentiality, processing_status="PROCESSING",
        checksum=checksum, doc_role=doc_role, version=version, status=status
    )
    db.add(doc)
    db.commit()
    create_audit_log(db, user_id=user.id, action="UPLOAD_DOCUMENT", detail=safe_name, project_id=project_id)

    try:
        pages = doc_parser.parse_document(filepath, ext)
        n_chunks = rag_store.ingest_document(doc.id, project_id, safe_name, pages, confidentiality, doc_role=doc.doc_role, version=doc.version)

        # Vision caption for images: run vision model and store as extra chunk
        vision_caption = None
        if ext in IMAGE_EXT:
            try:
                from ..agent.llm_client import vision_generate, LLMError
                image_b64 = base64.b64encode(content).decode("utf-8")
                caption = vision_generate(
                    settings.VISION_MODEL,
                    "Describe this image briefly. Focus on any technical data, labels, or measurements visible.",
                    image_b64,
                    max_tokens=200,
                )
                if caption:
                    vision_caption = caption
                    # Add vision-derived chunk to RAG
                    vision_pages = [{"page": 0, "text": f"[VISION-DERIVED CAPTION]: {caption}",
                                     "ocr_used": False, "low_confidence": False}]
                    rag_store.ingest_document(
                        f"{doc.id}_vision", project_id, f"{safe_name} (vision caption)",
                        vision_pages, confidentiality
                    )
                    n_chunks += 1
            except Exception:
                pass  # Vision is optional; if it fails, OCR path still works

        doc.processing_status = "DONE"
        doc.page_count = len(pages)
        db.commit()
        create_audit_log(db, user_id=user.id, action="RAG_INGEST", detail=f"{n_chunks} chunks", project_id=project_id)
        flagged = [p["page"] for p in pages if p.get("low_confidence")]
        result = {
            "id": doc.id, "filename": doc.filename, "status": doc.processing_status,
            "pages": len(pages), "chunks_indexed": n_chunks, "low_confidence_pages": flagged,
        }
        if vision_caption:
            result["vision_caption"] = vision_caption
        return result
    except Exception as e:
        doc.processing_status = "FAILED"
        db.commit()
        raise HTTPException(500, f"Processing failed: {e}")


@router.get("/project/{project_id}")
def list_documents(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _check_project_access(project_id, user, db)
    docs = db.query(Document).filter(Document.project_id == project_id).all()
    return [{
        "id": d.id, "filename": d.filename, "file_type": d.file_type,
        "status": d.processing_status, "pages": d.page_count,
        "confidentiality": d.confidentiality, "uploaded_at": d.created_at.isoformat(),
        "doc_role": d.doc_role, "version": d.version, "doc_status": d.status
    } for d in docs]


@router.get("/project/{project_id}/rules")
def get_project_rules(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Exposes the extracted rules strictly via a read-only endpoint so reviewers can verify what was pulled from each document.
    """
    _check_project_access(project_id, user, db)
    from ..tools import rag_store
    from ..agent import compliance
    
    chunks = rag_store.get_project_rules(project_id)
    rules = []
    for chunk_data in chunks:
        extracted = compliance._extract_rules(chunk_data["chunk"], chunk_data.get("filename", "unknown"), chunk_data.get("version", "1.0"), chunk_data.get("page", 1))
        for r in extracted:
            rules.append(r)
    return {"rules": rules}


from pydantic import BaseModel
class DocumentUpdate(BaseModel):
    doc_role: str
    version: str
    status: str


@router.put("/{doc_id}")
def update_document(
    doc_id: str,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
        
    _check_project_access(doc.project_id, user, db)
    
    doc.doc_role = payload.doc_role
    doc.version = payload.version
    doc.status = payload.status
    db.commit()
    
    # Also update RAG store metadata
    from ..tools.rag_store import _collection
    try:
        if _collection:
            res = _collection.get(where={"doc_id": doc_id})
            if res and "ids" in res and res["ids"]:
                metadatas = res["metadatas"]
                for m in metadatas:
                    m["doc_role"] = payload.doc_role
                    m["version"] = payload.version
                _collection.update(ids=res["ids"], metadatas=metadatas)
    except Exception as e:
        print(f"Warning: Failed to update RAG store metadata: {e}")
        
    create_audit_log(db, user.id, "UPDATE_DOCUMENT", f"Updated doc {doc_id} to {payload.doc_role} v{payload.version}")
    return {"status": "ok"}


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    _check_project_access(doc.project_id, user, db)

    if user.role != "ADMIN" and doc.uploader_id != user.id:
        raise HTTPException(403, "Only an ADMIN or the original uploader can delete this document")

    # 1. Delete from ChromaDB
    from ..tools.rag_store import delete_document as rag_delete
    rag_delete(doc_id)

    # 2. Delete file from disk
    if doc.filepath and os.path.exists(doc.filepath):
        try:
            os.remove(doc.filepath)
        except OSError as e:
            print(f"Warning: Failed to delete file {doc.filepath}: {e}")

    # 3. Delete from DB
    db.delete(doc)
    db.commit()

    # 4. Audit Log
    create_audit_log(db, user.id, "DOCUMENT_DELETE", f"Deleted doc {doc_id} ({doc.filename})", project_id=doc.project_id)

    return {"status": "ok"}
