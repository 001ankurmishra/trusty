# TrustForge Pilot Guide

Welcome to the TrustForge pilot program. TrustForge is an air-gapped, on-premise AI decision-support tool designed for industrial compliance validation.

## 1. Pilot Scope

The goal of this pilot is to evaluate TrustForge's ability to extract operating conditions from scanned inspection reports and validate them against internal Standard Operating Procedures (SOPs).

**During this pilot:**
- All document processing occurs strictly locally.
- 100% of network traffic is contained on the host machine.
- TrustForge acts as a **Decision Support System**. Final approval is *always* required by a human reviewer.

## 2. Acceptable Documents

For the duration of the pilot, please test the system with:
1. **SOPs / Limits Docs**: PDF or DOCX format containing operating limits (e.g. max pressure, min temperature).
2. **Inspection Reports**: PDF, DOCX, or Scanned Images (via Tesseract OCR) containing field measurements.

## 3. Roles and Responsibilities

- **Uploader (e.g., Inspector/Engineer):** Uploads the SOPs and Inspection Reports. Submits the validation task.
- **Reviewer (e.g., Compliance Officer):** Logs in to review the AI's extraction and verification. The Reviewer must manually sign off on the task before a compliance certificate is generated. (The Four-Eyes Principle).

## 4. Weekly Review Routine

To evaluate the success of the pilot, the designated project lead should perform a weekly review:
1. **False Positives:** Did the AI fail a document that was actually compliant?
2. **False Negatives:** Did the AI pass a document that was non-compliant?
3. **Extraction Accuracy:** Were the units correctly identified and normalized?

## 5. Success Metrics

At the end of the pilot (typically 4-6 weeks), the following metrics will be evaluated:
- Reduction in manual review time per document batch.
- Accuracy of automated limit violation detection.
- System stability on target hardware (16GB RAM laptop).
