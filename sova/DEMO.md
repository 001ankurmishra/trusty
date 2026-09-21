# TrustForge — Demo Script

Follow this script to demonstrate TrustForge's core capabilities in 3 minutes.

## 0. Preparation
1. Run `bash sova/scripts/run_all.sh` (ensure you are offline/disconnected from Wi-Fi to prove air-gap capabilities).
2. Run `./sova/backend/venv/bin/python3 sova/scripts/seed_demo.py` in a separate terminal.
3. Open `http://localhost:5173` in your browser.

## 1. The Setup (0:00 - 0:45)
- **Log in** using `admin` / `admin123`.
- Show the **Dashboard**: Point out that the Security status is "PROTECTED" (0 external calls).
- Navigate to the **Security Dashboard**:
  - Show the 4 hardware/security metrics.
  - Click **"Try to phone home"**. Show the red "BLOCKED" message and the counter incrementing.
  - This proves that even if the AI or a dependency tried to exfiltrate data, it would be stopped at the socket level.

## 2. Ingestion (0:45 - 1:30)
- Navigate to the **Dashboard** and click on the seeded project: **Sector 7 Safety Review**.
- Go to the **Documents** tab.
- Drag and drop the two generated files (`SOP_Pressure_Vessel.docx` and `Inspection_V-102.docx`) into the upload zone.
- Point out that parsing, OCR, and embedding are happening *locally*. Wait for status to turn to DONE.

## 3. The Workbench (1:30 - 2:30)
- Go to the **Workbench** tab.
- Type (or click the example): `"Analyze the inspection report for V-102 against our SOP limits and prepare an approval note."`
- Click **Run Task**.
- **Execution Timeline**: Watch the agent process live (Plan → Route → Retrieve → Reason → Verify).
- Point out the **Model Router** panel (showing which local model was selected and why).
- Review the **Result**:
  - Notice the deterministic **Compliance Comparison** table. The AI correctly identified that the 165 PSI measured pressure exceeds the 150 PSI limit.
  - Notice the **Verification** panel.

## 4. Human-in-the-Loop & Audit (2:30 - 3:00)
- Point out the **Human Review Required** box in the Workbench. The word "approval" triggered a four-eyes gate.
- *Wait, you are logged in as admin so you can override, but for best effect:*
  - In a new incognito window, log in as `reviewer` / `reviewer123`.
  - Go to Workbench, view the task.
  - Add a comment: `"Good catch on the pressure violation. Rejecting this inspection."`
  - Click **Reject** (or Approve if you prefer).
- Download the generated **DOCX Deliverable**. Show how it incorporates the AI's findings, citations, and the human reviewer's signature.
- Finally, navigate to the **Audit Log**.
  - Show the tamper-evident chain of events (upload, run task, approve/reject).
  - Click **Verify integrity** to prove the hashes align.

---

## What if something breaks?
- **Ollama unreachable**: Ensure `ollama serve` is running in another terminal.
- **Port in use**: Check if another instance of TrustForge is running (`killall node`, `killall Python`).
- **RAM limits**: If generation is extremely slow or fails, ensure no other heavy apps (Docker, Chrome with 100 tabs) are running.

## Honest Limitations (For Q&A)
- **Code Sandbox**: The Python sandbox is subprocess-based with AST checks. It's safe for demo purposes, but in production, we would swap it for a containerized sandbox (e.g. gVisor/Docker).
- **Vision Model**: `moondream` is small and fast, but struggles with highly complex engineering diagrams. We'd swap to `llava` for a production setup with a GPU.
- **Speed**: We are running 3 LLMs on CPU/unified memory simultaneously. Responses take ~15-30s. A dedicated server would make this near-instant.
