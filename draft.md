# TrustForge Status Report Draft

## STEP 1: Inventory
- Directories and lines analyzed via bash `find` and `wc -l`.
- `backend/app/agent/compliance.py`: 333 lines
- `frontend/src/pages/Workbench.jsx`: 478 lines
- total py/js/jsx/css/sh files: 7247 lines
- `REQUIREMENTS.md`: NOT FOUND

## STEP 2: Requirements Verification
(Will populate after checking FRs from codebase_for_claude.txt)

## STEP 3: Answers to Specific Questions

### Compliance Engine
1. **Does it read full SOP/report text, or only RAG-retrieved chunks?**
   It only reads RAG-retrieved chunks. In `orchestrator.py`, `sources = rag_store.search(...)` restricts texts to the top-k nearest chunks (below `RAG_DISTANCE_THRESHOLD`). `compliance.py` then only sees these chunks.
2. **How does it extract rules and measurements?**
   First via regex (e.g. `re.compile(r"(max|min)...")`). If regex yields nothing, it calls the LLM as a fallback. A fallback-derived row can produce PASS because the LLM output is appended to the main array if it passes strict hallucination rejection (the raw value must literally exist in the chunk's text).
3. **Is a measurement tied to a specific asset/tag?**
   Asset ID is extracted, but it's only used for computing deterministic corrosion rate. For general matching, `_fuzzy_match` only compares parameter words. Thus, two assets in one project could cross-match if both are in the retrieved chunks.
4. **What happens to an SOP rule that has no matching measurement?**
   It is silently dropped. The loop iterates over `measurements` and matches rules to them. A rule without a measurement is ignored, not emitted as `NEEDS_REVIEW`.
5. **Unit handling?**
   Supports: psi, bar, kpa, mm, in, cm, c, f, °c, celsius, °f, fahrenheit. It converts them to a base unit (pressure, length, temperature). It does not handle gauge vs absolute. It does not handle ranges or tolerances (regex only looks for max/min). If a parameter has multiple readings, the regex extracts all of them, resulting in multiple identical rows (which might match the rule or cause 'Ambiguous rules' if there are multiple rules).
6. **Is OCR confidence stored or used anywhere?**
   Yes. `doc_parser.py` sets `low_confidence: True` if `avg_conf < 60`. `rag_store.py` stores it. `orchestrator.py` checks it and sets `verification["low_confidence_sources_flagged"] = any(...)`.

### Audit Log & Security Monitor
7. **Are the rules used for a task snapshotted?**
   No. They are re-extracted live each time from the search chunks.
8. **Show create_audit_log(). Is there any lock or transaction protection?**
   There is no locking. `last_entry = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).first()` is executed without a transaction lock. Concurrent threads can fork the hash chain. No routers bypass `create_audit_log` directly, but the lack of locking is a vulnerability.
9. **Is the Ed25519 signature algorithm actually used?**
   Yes, `tasks_router.py` creates it (`private_key.sign(manifest_content)`). The script `scripts/verify_pack.py` correctly verifies it using `cryptography` primitives.
10. **Is `sandbox.py` using gVisor or just normal Docker?**
    Normal Docker (`docker run --rm --network none --memory 256m python:3.11-slim`). It does not mount the host environment, so it cannot steal the API key from environment variables (though it is not a robust VM-level sandbox like gVisor).
11. **How does the network patching intercept calls?**
    It monkey-patches `socket.socket.connect`, `connect_ex`, and `create_connection`. It covers urllib3/requests but sub-processes (like `os.system('curl')`) bypass it completely.
12. **If `OLLAMA_URL` points to an external server but `OUTBOUND_NETWORK=false`, does it block the Ollama calls?**
    Yes, unless the external IP/hostname is explicitly added to `OLLAMA_ALLOWED_HOSTS`.

### Task Workflow & Document Parsing
13. **What happens if a PDF is 200 pages long and takes 3 minutes to OCR during upload?**
14. **Is `sandbox.py` ever automatically invoked by the LLM?**
15. **Does the UI support assigning an Approval to a specific user?**
16. **If a user uploads a new version of an SOP, does it overwrite the old one in ChromaDB?**

### Auth & Security
17. **Is there any rate limiting on the login endpoint?**
18. **If the SECRET_KEY is leaked, can an attacker forge a JWT that never expires?**
19. **If `REQUIREMENTS.md` says 'R-19: Support Active Directory/LDAP', is it actually implemented?**

### Infrastructure
20. **Is there any connection pooling for SQLite?**
21. **Does the `scripts/setup_secrets.py` actually generate a `.env` file, or just print keys?**
