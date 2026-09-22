# TrustForge Verification Report

## Overview
This document serves as the final, evidence-based verification report for the TrustForge project. All tests were performed in an air-gapped simulation environment (Windows-compatible, 16GB RAM constraints, local models only) with network requests blocked.

## Security Hygiene (Step 0)
- **Status:** PASS
- **Findings:** The project repository no longer contains active admin JWT tokens (`token.json`). Secret keys are dynamically generated on initial run. TruffleHog CI checks are implemented to block accidental secrets from being pushed. 

## Compliance & Extraction Engine (Steps 1 & 6)
- **Status:** PASS
- **Findings:** The deterministic compliance extraction engine correctly cross-references parsed values against limits from SOPs.
  - **Unit mismatch:** Correctly fails when `10.5 bar` exceeds `150 PSI` (`10.5 bar = 152.28 PSI`).
  - **Missing SOP:** Correctly identifies missing compliance rules and flags parameters as `NEEDS_REVIEW`.
  - **Dimension mismatch:** Correctly identifies incompatible units (e.g., `90.0 PSI` for Wall Thickness) as `NEEDS_REVIEW`.
  - **Hallucination Rejection:** The deterministic extraction tables supersede LLM reasoning text for compliance decisions.

## Usability & Reliability (Steps 2 & 3)
- **Status:** PASS
- **Findings:** 
  - **Fail-open fallback:** The LLM client includes a fallback retry mechanism (e.g., routing to `qwen2.5-coder` if the primary model fails or times out) to ensure the system is highly reliable.
  - **Offline operation:** The application is entirely self-contained. The SentenceTransformers embedding model is pre-downloaded and forced offline via `HF_HUB_OFFLINE=1`.

## Model Layer (Step 4) & License Audit (Step E)
- **Status:** PASS
- **Findings:** The models selected operate efficiently within the 16GB RAM limit and do not require external API calls.
  - `qwen2.5-coder:1.5b` (Apache 2.0)
  - `moondream2` (Apache 2.0)
  - `all-MiniLM-L6-v2` (Apache 2.0)
  - `qwen2.5:3b-instruct` (Qwen Research License / Apache 2.0. Note: Alibaba releases various Qwen2.5 variants under Apache 2.0, but some specific models carry the Qwen Research License. Appropriate review of the specific downloaded GGUF weights is recommended for commercial use beyond 100M MAU).

## Operations & Delivery (Step 7)
- **Status:** PASS
- **Findings:**
  - **Air-Gapped Mode:** The custom `security_monitor.py` network guard successfully blocked outbound internet traffic to `8.8.8.8` (simulated via `/security/selftest`).
  - **Four-Eyes Principle:** The approval mechanism prevents a `USER` from approving their own submitted task, properly throwing a `403` error when attempted.
  - **Signed Audit Pack:** The system successfully generates a `.zip` artifact containing the source evidence, AI findings, compliance tables, human approval, and a cryptographic signature.
  - **Tamper Detection:** Manual tampering of the `audit_logs` database table breaks the SHA-256 hash chain and is properly flagged by the system as `TAMPERED`.
  - **Restart Recovery:** Stuck tasks (`RUNNING` / `RECEIVED`) are safely cleaned up and transitioned to `FAILED` during application startup (`lifespan` hook), preventing corrupted state across system reboots.

## Conclusion
TrustForge meets all core architectural and security constraints. The system has been validated to function correctly in a local, air-gapped, zero-trust environment using localized lightweight models.
