# TrustForge Security Architecture

TrustForge is designed to operate securely in high-compliance industrial environments.

## Air-Gapped Architecture & Telemetry
TrustForge operates entirely without outbound internet access at runtime.
- **Zero Telemetry**: All external API calls, analytics, and tracking have been disabled.
- **Local Models**: The reasoning engine uses local LLMs (e.g., Qwen 2.5 3B via Ollama) and local embedding models (`all-MiniLM-L6-v2` via SentenceTransformers). No data is sent to external AI providers.
- **Network Guard**: The `security_monitor` module verifies that outbound HTTP requests (e.g., to Google DNS or cloud endpoints) are blocked, actively monitoring socket connections.

## Deterministic Computations & Hallucination Rejection
To prevent LLM hallucination and ensure industrial safety:
- **Calculator Tool**: All arithmetic for corrosion rates and remaining life is executed deterministically in a strict Python AST environment (`app/tools/calculator.py`). The LLM does not perform math.
- **String Presence Checks**: If regex extraction fails and the system falls back to the LLM for variable extraction, every extracted number is strictly verified against the source text. If a number does not physically exist in the text, it is rejected as a hallucination.

## Cryptographic Traceability
- **Tamper-Evident Audit Log**: All system actions are stored in an SQLite database using a cryptographic hash chain. Each log entry is hashed along with the `prev_hash` (similar to a blockchain) so that any modification to historical data will break the chain and raise a tampering alert.
- **Ed25519 Document Signing**: When an approval note is generated, the backend uses Ed25519 public key cryptography to sign the document payload (timestamp, user, findings). This signature is injected directly into the DOCX file's custom properties and can be verified entirely offline using the provided `verify_audit.py` script.

## Access Control
- **Four-Eyes Principle**: A task created by an inspector cannot be approved by the same user. An independent REVIEWER or ADMIN must provide final approval.
- **Role-Based Access**: The system enforces `ADMIN`, `REVIEWER`, and `USER` roles, separating concerns between executing compliance checks and granting final sign-off.

## Purging Secrets from History
If a secret (like `token.json` or `public_key.pem`) is accidentally committed to the repository, it is not enough to simply delete it or add it to `.gitignore`. You must purge it from the Git history using `git filter-repo`.
```bash
# Install git-filter-repo
pip install git-filter-repo

# Purge the leaked file from all historical commits
git filter-repo --invert-paths --path sova/backend/public_key.pem --path token.json

# Force push to the remote repository (use caution!)
git push origin --force --all
```
