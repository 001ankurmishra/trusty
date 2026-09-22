# TrustForge — Laptop-Scoped MVP (16GB RAM / 512GB SSD, no Streamlit)

This is a working scope-down of the full TrustForge spec, sized to run **entirely on a
16GB RAM laptop with CPU-only inference** (works fine even without a dedicated
GPU). It keeps every judge-visible checkpoint from the requirements doc:

- Local models only (via **Ollama**, not vLLM — vLLM needs a real GPU)
- FastAPI backend + **React (Vite + Tailwind)** frontend — no Streamlit
- Model router with visible model + reason
- Local OCR (Tesseract) + PDF/DOCX/XLSX parsing
- Local RAG: **ChromaDB embedded** (no server/container) + sentence-transformers
  embeddings, instead of Qdrant — same retrieval behavior, ~1/10th the RAM
- Agent state machine (plan → route → retrieve → tool → verify → approve → deliver)
- Calculator + Python sandbox tools
- DOCX "Inspection Approval Note" generation + quality check
- RBAC (ADMIN/USER/REVIEWER), human-in-the-loop approval
- Security dashboard proving **zero external network calls** (socket-level guard)
- Audit log, AI Work Receipt

### Why these substitutions
| Spec asked for | Swapped for | Why |
|---|---|---|
| vLLM, 16-24GB VRAM models | **Ollama**, 1.5B–3B quantized models | Runs on CPU-only, 16GB RAM |
| Qdrant + Docker | **ChromaDB embedded** | No server/container, ~50MB footprint |
| PostgreSQL | **SQLite** | Zero setup, single file |
| Redis | *(dropped for MVP)* | Not needed at this scale; task state lives in SQLite |
| PaddleOCR | **Tesseract** (pytesseract) | Much lighter install, same OCR job |
| Docker sandbox | **subprocess sandbox** w/ timeout + network-disabled | Reliable without requiring Docker Desktop set up tonight |
| Streamlit | **React + Vite + Tailwind** | As requested |

Everything above is a drop-in upgrade path later (swap ChromaDB→Qdrant,
SQLite→Postgres, subprocess→Docker) without changing the API shape.

---

## 1. Prerequisites (install once)

1. **Python 3.11+** and **Node.js 20+**
2. **Ollama** — https://ollama.com/download (this is the "local model server")
3. **Tesseract OCR** binary:
   - Windows: https://github.com/UB-Mannheim/tesseract/wiki (installer)
   - Mac: `brew install tesseract`
   - Linux: `sudo apt install tesseract-ocr`

## 2. Pull the local models (one-time, needs internet; after this, fully offline)

Open a terminal:
```bash
ollama pull llama3.2                  # reasoning — ~2GB
ollama pull qwen2.5-coder:1.5b        # coding — ~1GB
ollama pull moondream                 # vision — ~1.7GB
```
These three together comfortably fit in 16GB RAM since Ollama loads one at a
time on demand. Total disk: ~6GB, well inside 512GB.

## 3. Automated Setup

To set up everything (backend venv, dependencies, embedding models, `.env`, admin user, frontend deps) in one go:

**Mac / Linux:**
```bash
bash sova/scripts/setup.sh
```

**Windows:**
```powershell
powershell .\sova\scripts\setup.ps1
```

## 4. Running TrustForge

To start both the backend and frontend simultaneously:

**Mac / Linux:**
```bash
bash sova/scripts/run_all.sh
```

**Windows:**
```powershell
powershell .\sova\scripts\run_all.ps1
```

The frontend runs at http://localhost:5173 (log in as `admin` / `admin123`).
The backend runs at http://localhost:8000.

## 5. Demo script for tomorrow

Please refer to [DEMO.md](file:///Users/ankurmishra/Documents/CODE/TrustForge-main/sova/DEMO.md) for a full 3-minute demo script you can run.

1. **Dashboard** — create a project ("Refinery Inspection Q1").
2. **Documents** — drag in a sample inspection PDF (scanned or text) and an
   internal SOP PDF. Watch status go PENDING → DONE (OCR + RAG ingestion).
3. **Workbench** — type:
   > "Analyze this inspection report, compare with our internal SOP, and prepare an approval note."
4. Watch the **Execution Timeline** run live: task classified → model selected
   → knowledge retrieved → verification → human review required → artifact
   generated.
5. Point out the **Model Router** panel (which local model, why) and the
   **Sources/Evidence** panel (page-level citations, low-confidence OCR flags).
6. Log out, log in as `reviewer` / `reviewer123`, approve the task.
7. Download the generated **Inspection_Approval_Note.docx**.
8. Open **Security** tab — show `external calls: 0`, air-gapped mode ON, and
   the live socket event log proving nothing left the laptop.
9. Open **Audit Log** — show every action logged with timestamps.

Also show the standalone demos to hit P1 items:
- A coding-style task ("write a Python function to check pressure vessel
  thickness against a minimum, and run it") → routes to the coding model,
  executes in the sandbox, shows stdout.
- A pure calculation task → calculator tool + verification flag.

## 6. If something breaks 10 minutes before judging

- **Ollama not responding**: run `ollama serve` in a terminal; keep it open.
- **Model too slow on stage**: swap `REASONING_MODEL` in `.env` to a smaller
  model, e.g. `qwen2.5:1.5b-instruct` (`ollama pull` it first), restart uvicorn.
- **OCR errors**: confirm `tesseract` is on PATH (`tesseract --version`).
- Keep a **pre-run project** with documents already uploaded and one task
  already completed as a fallback if live inference is slow during Q&A.

## 7. Full requirements traceability

Everything in `SOVA_requirements.txt` sections 3–4 (FR-01…FR-26, NFR-01…08) is
implemented at MVP depth except: PPTX/XLSX generation, Prometheus/Grafana,
Keycloak (using JWT/RBAC instead, which the spec explicitly allows), and
Docker-based sandboxing (subprocess sandbox instead — see substitution table
above). These are the P2/optional items in the spec's own priority list.
