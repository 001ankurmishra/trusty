#!/usr/bin/env python3
"""
TrustForge — Environment Check
Verifies all prerequisites are met before running TrustForge.
Usage: python sova/scripts/check_env.py
"""
import shutil
import subprocess
import sys
import socket

PASS = "\033[92m PASS \033[0m"
FAIL = "\033[91m FAIL \033[0m"
WARN = "\033[93m WARN \033[0m"

results = []

def check(name, ok, detail=""):
    status = PASS if ok else FAIL
    results.append((name, ok))
    print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ""))


print("╔══════════════════════════════════════════╗")
print("║   TrustForge — Environment Check         ║")
print("╚══════════════════════════════════════════╝\n")

# 1. Python version
py_version = sys.version_info
check("Python 3.11+", py_version >= (3, 11), f"found {py_version.major}.{py_version.minor}.{py_version.micro}")

# 2. Node.js version
try:
    node_out = subprocess.check_output(["node", "--version"], text=True).strip()
    node_major = int(node_out.lstrip("v").split(".")[0])
    check("Node.js 20+", node_major >= 20, f"found {node_out}")
except Exception:
    check("Node.js 20+", False, "not found — install from https://nodejs.org")

# 3. Ollama binary
ollama_path = shutil.which("ollama")
check("Ollama binary", ollama_path is not None, ollama_path or "not found — install from https://ollama.com")

# 4. Tesseract binary
tess_path = shutil.which("tesseract")
if tess_path is None and sys.platform == "win32":
    win_tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if __import__("os").path.exists(win_tess):
        tess_path = win_tess

check("Tesseract OCR", tess_path is not None, tess_path or "not found — install Tesseract (Windows: https://github.com/UB-Mannheim/tesseract/wiki)")

# 5. Ollama models
# Read from config to avoid hardcoding
try:
    sys.path.insert(0, __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "backend")))
    from app.core.config import settings
    REQUIRED_MODELS = [settings.REASONING_MODEL, settings.CODING_MODEL, settings.VISION_MODEL]
except Exception as e:
    REQUIRED_MODELS = ["qwen2.5:3b-instruct", "qwen2.5-coder:1.5b", "moondream"]

try:
    import requests
    resp = requests.get("http://localhost:11434/api/tags", timeout=3)
    installed = [m["name"] for m in resp.json().get("models", [])]
    for model in REQUIRED_MODELS:
        found = any(model.split(":")[0] in inst for inst in installed)
        check(f"Ollama model: {model}", found, "installed" if found else "run: ollama pull " + model)
except Exception:
    for model in REQUIRED_MODELS:
        check(f"Ollama model: {model}", False, "Ollama not responding — run 'ollama serve'")

# 6. Embedding model cached
try:
    from sentence_transformers import SentenceTransformer
    import os
    # Check if cached without downloading
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "torch", "sentence_transformers")
    huggingface_cache = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
    cached = (
        os.path.exists(os.path.join(cache_dir, "sentence-transformers_all-MiniLM-L6-v2"))
        or any("all-MiniLM-L6-v2" in d for d in os.listdir(huggingface_cache) if os.path.isdir(huggingface_cache))
    )
    if not cached:
        # Try loading it — this is fine if it is cached somewhere else
        try:
            os.environ["HF_HUB_OFFLINE"] = "1"
            SentenceTransformer("all-MiniLM-L6-v2")
            cached = True
        except Exception:
            cached = False
    check("Embedding model cached", cached, "all-MiniLM-L6-v2" if cached else "Run setup.sh to cache it while online")
except ImportError:
    check("Embedding model cached", False, "sentence-transformers not installed")

# 7. Ports free
for port in [8000, 5173]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.bind(("127.0.0.1", port))
        s.close()
        check(f"Port {port} free", True)
    except OSError:
        check(f"Port {port} free", False, f"port {port} is in use — stop the process using it")

print()
passed = sum(1 for _, ok in results if ok)
total = len(results)
if passed == total:
    print(f"  ✅  All {total} checks passed! Ready to run.")
else:
    print(f"  ⚠   {passed}/{total} checks passed. Fix the FAIL items above.")
print()
