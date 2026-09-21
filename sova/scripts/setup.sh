#!/usr/bin/env bash
# TrustForge — one-time setup script for macOS/Linux
# Usage: bash sova/scripts/setup.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════╗"
echo "║   TrustForge — Setup (macOS / Linux)     ║"
echo "╚══════════════════════════════════════════╝"

# --- Backend venv + deps ---
echo -e "\n[1/6] Creating Python virtual environment…"
cd "$ROOT/backend"
python3 -m venv venv
source venv/bin/activate
echo "[2/6] Installing Python dependencies…"
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pytest httpx -q  # test deps

# --- Cache the embedding model while online ---
echo "[3/6] Caching sentence-transformers embedding model (one-time download)…"
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# --- Create .env if it doesn't exist ---
if [ ! -f .env ]; then
    echo "[3b] Creating .env from .env.example with random SECRET_KEY…"
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    sed "s/change-me-to-something-random/$SECRET/" .env.example > .env
fi

# --- Pull Ollama models ---
echo "[4/6] Pulling Ollama models (needs internet, ~6 GB total)…"
echo "  Make sure 'ollama serve' is running in another terminal."
ollama pull qwen2.5:3b-instruct || echo "  ⚠ Could not pull qwen2.5:3b-instruct — pull manually later"
ollama pull qwen2.5-coder:1.5b   || echo "  ⚠ Could not pull qwen2.5-coder:1.5b — pull manually later"
ollama pull moondream             || echo "  ⚠ Could not pull moondream — pull manually later"

# --- Bootstrap admin users ---
echo "[5/6] Bootstrapping admin + reviewer users…"
python bootstrap_admin.py

# --- Frontend ---
echo "[6/6] Installing frontend dependencies…"
cd "$ROOT/frontend"
npm install

echo ""
echo "✅  Setup complete!"
echo "    Run:  bash sova/scripts/run_all.sh"
