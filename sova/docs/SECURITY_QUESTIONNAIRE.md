# TrustForge IT Security Questionnaire

This document provides pre-filled answers to common IT security questions for enterprise deployment.

## Network & Connectivity
**Q: Does the application require internet access to function?**
A: **No.** TrustForge is designed to run in a 100% air-gapped environment. After initial installation (which requires downloading the Docker images or Python wheels / Ollama models), the system functions entirely offline.

**Q: Are any third-party cloud services used for data processing (e.g., OpenAI, AWS, Azure)?**
A: **No.** All data processing, including Large Language Model (LLM) inference and Optical Character Recognition (OCR), happens entirely on the local machine using Ollama and Tesseract.

**Q: Does the application "phone home" for telemetry or updates?**
A: **No.** There is no telemetry, tracking, or automatic update mechanism built into the software.

## Data Storage & Encryption
**Q: Where is data stored?**
A: All data is stored locally in a SQLite database (`trustforge.db`) and a ChromaDB vector store directory, both located on the host filesystem. Uploaded files are stored in a local `./uploads` directory.

**Q: Is data encrypted at rest?**
A: TrustForge relies on the host operating system for encryption at rest (e.g., BitLocker on Windows or FileVault on macOS).

**Q: How is data protected in transit?**
A: If deployed locally on a laptop, traffic never leaves `localhost`. If deployed on an internal server, we strongly recommend placing it behind a reverse proxy (e.g., Nginx) configured with TLS/SSL for HTTPS.

## Application Security
**Q: What mitigations are in place against Server-Side Request Forgery (SSRF) and data exfiltration?**
A: The backend implements a low-level network guard (`security_monitor.py`) that monkey-patches the Python `socket` library. It explicitly blocks all outbound network connections except for localhost and specific hostnames allowed in the `OLLAMA_ALLOWED_HOSTS` configuration.

**Q: How is authentication handled?**
A: TrustForge uses JSON Web Tokens (JWT) for authentication. Passwords are hashed using bcrypt before storage. Default admin credentials must be changed on first login.

**Q: Are secrets or API keys stored in the source code?**
A: **No.** The system enforces the use of a strongly generated `SECRET_KEY` in production environments. Any short or default keys will cause the application to crash on startup in production mode.

## Dependency Management
**Q: Are software dependencies scanned for vulnerabilities?**
A: Yes. The CI/CD pipeline includes secret scanning (GitLeaks) and dependency checking. A `wheelhouse` bundle is provided for offline, deterministic installation to prevent supply chain attacks during deployment.
