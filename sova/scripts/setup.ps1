<#
.SYNOPSIS
    TrustForge — one-time setup script for Windows
.DESCRIPTION
    Creates Python virtual environment, installs dependencies, pulls Ollama models,
    bootstraps admin users, and installs frontend dependencies.
#>

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ROOT = Split-Path -Parent $SCRIPT_DIR

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   TrustForge - Setup (Windows)           " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# --- Backend venv + deps ---
Write-Host "`n[1/6] Creating Python virtual environment..." -ForegroundColor Yellow
Set-Location -Path "$ROOT\backend"
python -m venv venv
$env:Path = "$ROOT\backend\venv\Scripts;" + $env:Path

Write-Host "[2/6] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
python -m pip install pytest httpx -q

# --- Cache the embedding model ---
Write-Host "[3/6] Caching sentence-transformers embedding model (one-time download)..." -ForegroundColor Yellow
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# --- Create .env if it doesn't exist ---
if (-not (Test-Path ".env")) {
    Write-Host "[3b] Creating .env from .env.example with random SECRET_KEY..." -ForegroundColor Yellow
    $SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
    (Get-Content ".env.example") -replace 'change-me-to-something-random', $SECRET | Set-Content ".env"
}

# --- Pull Ollama models ---
Write-Host "[4/6] Pulling Ollama models (needs internet, ~6 GB total)..." -ForegroundColor Yellow
Write-Host "  Make sure 'ollama serve' is running." -ForegroundColor Gray

try { ollama pull qwen2.5:3b-instruct } catch { Write-Host "  WARNING: Could not pull qwen2.5:3b-instruct" -ForegroundColor Red }
try { ollama pull qwen2.5-coder:1.5b } catch { Write-Host "  WARNING: Could not pull qwen2.5-coder:1.5b" -ForegroundColor Red }
try { ollama pull moondream } catch { Write-Host "  WARNING: Could not pull moondream" -ForegroundColor Red }

# --- Bootstrap admin users ---
Write-Host "[5/6] Bootstrapping admin + reviewer users..." -ForegroundColor Yellow
python bootstrap_admin.py

# --- Frontend ---
Write-Host "[6/6] Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location -Path "$ROOT\frontend"
npm install

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "Run: powershell .\sova\scripts\run_all.ps1" -ForegroundColor Cyan
