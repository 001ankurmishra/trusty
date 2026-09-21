#!/usr/bin/env bash
# TrustForge — start backend + frontend
# Usage: bash sova/scripts/run_all.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════╗"
echo "║   TrustForge — Run All                   ║"
echo "╚══════════════════════════════════════════╝"

# Recommended Ollama settings for 16GB RAM
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_NUM_PARALLEL=1

# --- Start Ollama if not already running ---
if ! pgrep -x ollama > /dev/null 2>&1 && ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[1] Starting Ollama serve…"
    ollama serve &
    OLLAMA_PID=$!
    sleep 3
    echo "    Ollama PID: $OLLAMA_PID"
else
    echo "[1] Ollama is already running."
fi

# --- Start backend ---
echo "[2] Starting FastAPI backend on http://localhost:8000 …"
cd "$ROOT/backend"
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo "    Backend PID: $BACKEND_PID"

# --- Start frontend ---
echo "[3] Starting Vite dev server on http://localhost:5173 …"
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
echo "    Frontend PID: $FRONTEND_PID"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   TrustForge is running!                 ║"
echo "║                                          ║"
echo "║   Frontend: http://localhost:5173         ║"
echo "║   Backend:  http://localhost:8000         ║"
echo "║   API docs: http://localhost:8000/docs    ║"
echo "║                                          ║"
echo "║   Login:    admin / admin123              ║"
echo "║             reviewer / reviewer123        ║"
echo "║                                          ║"
echo "║   Press Ctrl+C to stop all services.     ║"
echo "╚══════════════════════════════════════════╝"

# Trap SIGINT to stop all background processes
cleanup() {
    echo -e "\n[Stopping services…]"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    [ -n "${OLLAMA_PID:-}" ] && kill $OLLAMA_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for any background process to exit
wait
