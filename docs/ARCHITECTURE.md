# TrustForge Architecture

## Overview
TrustForge is an air-gapped, on-premise AI workbench designed for confidential enterprise operations (e.g., inspection and compliance review).

## Core Components
- **Backend**: FastAPI
- **Database**: SQLite (SQLAlchemy ORM)
- **Vector Store**: ChromaDB (local persistence)
- **Local LLM**: Ollama (runs locally, default reasoning model: `qwen2.5:3b-instruct`)
- **Frontend**: React 18, Vite, TailwindCSS

## Data Flow
1. **Document Upload**: Users upload documents (PDF, DOCX, XLSX, images). The `doc_parser` extracts text (using PyMuPDF, docx, openpyxl, or Tesseract OCR for images/scans).
2. **Indexing**: Extracted chunks are embedded (via SentenceTransformers, e.g., `all-MiniLM-L6-v2`) and stored in ChromaDB within `storage/chroma_db/`.
3. **Task Orchestration**: 
   - User submits a task query.
   - The Orchestrator (`orchestrator.py`) handles the execution synchronously via a thread-pool, while the HTTP request returns the task ID immediately.
   - **Model Router**: Routes tasks to local LLMs based on intent (reasoning, coding, extraction).
   - **RAG Retrieval**: Searches ChromaDB for relevant chunks based on the project boundary.
   - **Compliance Engine**: Deterministically extracts rules (`max/min ...: value unit`) and measurements from retrieved context and fuzzy matches parameters to evaluate `PASS` or `FAIL` deterministically without LLM hallucinations.
   - **LLM Reasoning**: Generates text grounded heavily in the retrieved context using safe prompt barriers.
   - **Verification**: Evaluates grounding, flagging low-confidence OCR sources and checking that numbers match the source.
4. **Deliverable Generation**: Generates a formatted DOCX approval note (`docgen.py`) and computes a SHA-256 hash.
5. **Human Review (Four-Eyes)**: High-impact tasks require approval by a different user with a `REVIEWER` or `ADMIN` role. Artifact downloads are gated until approval.
6. **Audit Logs**: Actions are logged securely with an Ed25519-like / SHA-256 tamper-evident hash chain in SQLite.
7. **Security Monitor**: A global network guard monitors `socket.socket` to log and block unauthorized external egress, ensuring air-gap compliance.
