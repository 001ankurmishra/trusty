# TrustForge (SOVA) Status Report

**Date:** September 2026
**Auditor:** Senior Software Auditor
**Scope:** Read-only inspection of the TrustForge MVP repository

---

## STEP 1: Inventory

### Directory Tree & Line Counts
A full tree scan was performed on `backend/app/`, `backend/tests/`, `backend/alembic/`, `frontend/src/`, `scripts/`, and `.github/`.
- **Total relevant source lines:** ~7,247 lines.
- **Largest Components:** 
  - `frontend/src/pages/Workbench.jsx` (478 lines)
  - `backend/app/routers/tasks_router.py` (501 lines)
  - `backend/app/agent/orchestrator.py` (364 lines)
  - `backend/app/agent/compliance.py` (333 lines)
- **Git History Summary:** 19 commits total, originating from "TrustForge Engineering Overhaul MVP".
- **Secrets/Large Files:** Checked tracked files for `.pem`, `.key`, `token*.json`, `.env`, and `.db`. Only `.env.example` is tracked. The repository is free of committed raw secrets.

### Configuration Analysis
- **Python Dependencies:** `fastapi`, `uvicorn`, `sqlalchemy`, `chromadb`, `sentence-transformers`, `pymupdf`, `pytest`, etc.
- **Frontend Dependencies:** React 18, Vite, Tailwind CSS, React Router DOM.
- **Environment config:** Default secrets are guarded by a validation check requiring `APP_ENV=development` if default keys are used. 

---

## STEP 2: Requirements Verification

> **NOTE: `REQUIREMENTS.md` was NOT FOUND in the repository.** Verification relies on `codebase_for_claude.txt` and explicit system design claims.

**Verified FR/NFRs:**
- **Local OCR/Parsing:** Implemented using `pytesseract` and `pymupdf` in `app/tools/doc_parser.py`.
- **Local RAG:** Implemented using embedded `ChromaDB` and `sentence-transformers` in `app/tools/rag_store.py`.
- **Local LLM Inference:** Ollama integration verified in `app/agent/llm_client.py`.
- **RBAC & Auth:** JWT auth and user roles implemented in `app/core/auth.py`.
- **Security Dashboard & Network Guard:** Subprocess-level and Socket-level outbound restrictions implemented in `app/core/security_monitor.py`.
- **Sandbox execution:** Implemented via `docker run --rm --network none python:3.11-slim` in `app/tools/sandbox.py`.

**Gaps/Missing:**
- Active Directory / LDAP support is NOT FOUND.
- `REQUIREMENTS.md` is missing entirely.

---

## STEP 3: Specific System Questions

### Compliance Engine (`app/agent/compliance.py`)
1. **Does it read full SOP/report text, or only RAG-retrieved chunks?**
   **Answer:** It only reads RAG-retrieved chunks. The orchestrator calls `rag_store.search` to retrieve the top 5 chunks with a distance below the `RAG_DISTANCE_THRESHOLD`, and passes only those to the compliance engine.
2. **How does it extract rules and measurements? What triggers LLM fallback?**
   **Answer:** It extracts them primarily using regex (e.g. `re.compile(r"(max|min)...")`). If the regex yields zero matches, it triggers the LLM fallback (`generate()`). A fallback-derived row **can** produce PASS because the LLM-extracted rules are strictly verified against hallucination (the value string must literally exist in the chunk's source text) and are appended to the main rules array for identical subsequent processing.
3. **Is a measurement tied to a specific asset/tag, or matched by project/role? Could two assets cross-match?**
   **Answer:** While asset IDs are extracted to compute deterministic corrosion rates, they are **not** used to bound general compliance rules. The `_fuzzy_match` function only compares parameter words. Therefore, it **is** possible for a measurement of "Pressure" on V-101 to cross-match with an SOP limit intended for V-102 if both chunks are retrieved simultaneously.
4. **What happens to an SOP rule that has no matching measurement?**
   **Answer:** It is silently dropped. The matching loop iterates over the `measurements` array; any rule in the `rules` array that does not match a measurement is completely ignored and does NOT emit a `NEEDS_REVIEW` row.
5. **Unit handling?**
   **Answer:** Supported units: `psi`, `bar`, `kpa`, `mm`, `in`, `cm`, `c`, `f` (and aliases). It converts these to base units. It does **not** handle gauge vs absolute pressure, ranges, or tolerances (regex only looks for explicitly "max" or "min"). If a parameter has multiple readings, the regex extracts all of them, resulting in multiple rows (which may trigger an "Ambiguous rules" exception if multiple rules match).

### Task Workflow & Document Parsing
6. **Is OCR confidence stored or used anywhere?**
   **Answer:** Yes. `doc_parser.py` flags pages where `avg_conf < 60`. `rag_store.py` preserves this metadata, and `orchestrator.py` checks it to set the `low_confidence_sources_flagged` verification flag.
7. **Are the rules used for a task snapshotted on the Task?**
   **Answer:** No. They are re-extracted live on-the-fly during each task execution from the retrieved ChromaDB chunks.
13. **What happens if a PDF takes 3 minutes to OCR during upload?**
   **Answer:** The OCR and ChromaDB ingestion happen **synchronously** in the FastAPI endpoint `POST /api/documents/upload` (`doc_parser.parse_document` and `rag_store.ingest_document`). The HTTP request will block, potentially causing a client-side or reverse-proxy timeout.
14. **Is `sandbox.py` ever automatically invoked by the LLM?**
   **Answer:** Yes. In `orchestrator.py` (line 205), if the task is classified as a coding task, the orchestrator prompts the LLM to generate code, cleans it, and automatically executes `sandbox.run_python(code)`.
15. **Does the UI support assigning an Approval to a specific user?**
   **Answer:** No. There is no `assignee_id` field on the `Task` model, and any user with project access can approve a task in the UI.
16. **If a user uploads a new version of an SOP, does it overwrite the old one in ChromaDB?**
   **Answer:** No. `upload_document` assigns a random UUID prefix to the filename and creates a new DB entry and ChromaDB chunks. Unless the user explicitly calls `DELETE /api/documents/{id}`, the old chunks remain active in the knowledge base.

### Audit Log & Security
8. **Show create_audit_log(). Is there any lock or transaction protection?**
   **Answer:** No transaction locks are used. `last_entry = db.query(AuditLog)...first()` fetches the previous hash, and then the row is committed. Concurrent threads logging simultaneously will fetch the same `prev_hash` and fork the hash chain.
9. **Is the Ed25519 signature algorithm actually used for the ZIP export?**
   **Answer:** Yes. The export in `tasks_router.py` loads the PEM private key and signs the SHA-256 hashes inside `manifest.txt`. `verify_pack.py` successfully verifies this signature using `cryptography` primitives.
10. **Is `sandbox.py` using gVisor, or just normal Docker? Can the LLM steal the API key?**
   **Answer:** It uses normal Docker (`docker run --rm --network none --memory 256m python:3.11-slim`). Since environment variables (like `SECRET_KEY`) are not mounted into the container, the LLM cannot steal them, despite it not being a true VM-level sandbox like gVisor.
11. **How does the network patching intercept calls? Are sub-processes protected?**
   **Answer:** It monkey-patches `socket.socket.connect`, `connect_ex`, and `create_connection` in `security_monitor.py`. Python libraries like `urllib3` and `requests` are blocked. However, subprocesses (e.g. `os.system("curl ...")`) are **not** protected by this patch because they execute outside the Python runtime.
12. **If OLLAMA_URL points to an external server but OUTBOUND_NETWORK=false, does it block the Ollama calls?**
   **Answer:** Yes, the security monitor explicitly checks if the host is in `settings.OLLAMA_ALLOWED_HOSTS` or `127.0.0.1`. If it's external and not allowed, it blocks the connection.
17. **Is there any rate limiting on the login endpoint?**
   **Answer:** Yes. `auth_router.py` implements a simple in-memory rate limiting dictionary tracking `count` and `locked_until` per username.
18. **If the SECRET_KEY is leaked, can an attacker forge a JWT that never expires?**
   **Answer:** Yes. The `python-jose` library's `jwt.decode` does not enforce the presence of an `exp` claim by default unless `options={"require": ["exp"]}` is explicitly passed. An attacker could forge a token omitting the `exp` claim entirely.
19. **Is Active Directory/LDAP implemented?**
   **Answer:** NOT FOUND.

### Infrastructure
20. **Is there any connection pooling for SQLite?**
   **Answer:** No dedicated queue pool is configured. SQLAlchemy defaults to `SingletonThreadPool` when `check_same_thread=False` is passed to SQLite.
21. **Does the `scripts/setup_secrets.py` actually generate a `.env` file?**
   **Answer:** Yes, it appends a randomly generated `SECRET_KEY` and the Ed25519 paths to `.env`.

---

## STEP 4: Testing

- A full suite run (`pytest tests/ -v`) was executed locally in the backend environment.
- **Total Tests:** 19
- **Results:** 18 PASSED, 1 FAILED.
- **Failures:** `test_golden_compliance` failed because it explicitly tests the LLM fallback extraction path, which requires a running Ollama server. Since Ollama is not running in this environment, it raised `LLM measurement extraction failed: Could not reach local Ollama server...`.
- **Coverage:** Model fallback logic and Sandbox validation logic are covered. No tests failed due to Alembic vs `create_all` database mismatches (resolved in prior work).

---

## STEP 5: Frontend Inspection

The UI is built using React Router with the following active pages:
- `/` -> Dashboard
- `/workbench` -> Workbench
- `/documents` -> Documents
- `/rules` -> Rules
- `/inbox` -> Inbox
- `/models` -> ModelRouterPage
- `/metrics` -> Metrics
- `/security` -> Security
- `/audit` -> Audit

All routes are fully implemented and wrapped in a `<Protected>` layout.

---

## STEP 6: Doc-Code Discrepancies

1. **`REQUIREMENTS.md`**: Missing entirely from the `docs/` folder, contradicting instructions.
2. **Docker Sandboxing Claims**: The code explicitly admits in `sandbox.py` docstrings that it is a "HONEST LIMITATION" using a best-effort subprocess/docker wrapper, contradicting any claims of high-security gVisor sandboxing.
3. **Synchronous document parsing**: The documentation often claims scalable AI extraction, but parsing large PDFs currently blocks the HTTP thread entirely, making it unscalable for production loads.

---
**End of Report**
