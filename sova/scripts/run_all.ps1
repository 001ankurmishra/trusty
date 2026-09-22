<#
.SYNOPSIS
    TrustForge — start backend + frontend (Windows)
.DESCRIPTION
    Starts Ollama (if not running), FastAPI backend, and Vite frontend.
#>

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ROOT = Split-Path -Parent $SCRIPT_DIR

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   TrustForge - Run All (Windows)         " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_NUM_PARALLEL = "1"

$jobs = @()

# --- Start Ollama if not already running ---
$ollamaRunning = $false
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -ErrorAction Stop
    $ollamaRunning = $true
} catch {
    $ollamaRunning = $false
}

if (-not $ollamaRunning) {
    Write-Host "[1] Starting Ollama serve..." -ForegroundColor Yellow
    $ollamaJob = Start-Job -ScriptBlock { ollama serve }
    $jobs += $ollamaJob
    Start-Sleep -Seconds 3
} else {
    Write-Host "[1] Ollama is already running." -ForegroundColor Green
}

# --- Start backend ---
Write-Host "[2] Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location -Path "$root\backend"
    $env:Path = "$root\backend\venv\Scripts;" + $env:Path
    uvicorn app.main:app --host 127.0.0.1 --port 8000
} -ArgumentList $ROOT
$jobs += $backendJob

# --- Start frontend (if dist/ doesn't exist or we want dev mode) ---
$distPath = Join-Path -Path $ROOT -ChildPath "frontend\dist"
if (Test-Path $distPath) {
    Write-Host "[3] Frontend dist/ found. It will be served statically by the backend." -ForegroundColor Green
} else {
    Write-Host "[3] Starting Vite dev server on http://localhost:5173 ..." -ForegroundColor Yellow
    $frontendJob = Start-Job -ScriptBlock {
        param($root)
        Set-Location -Path "$root\frontend"
        npm run dev
    } -ArgumentList $ROOT
    $jobs += $frontendJob
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "   TrustForge is running!                 " -ForegroundColor Green
Write-Host "                                          "
Write-Host "   Frontend: http://localhost:5173        " -ForegroundColor Cyan
Write-Host "   Backend:  http://localhost:8000        " -ForegroundColor Cyan
Write-Host "   API docs: http://localhost:8000/docs   " -ForegroundColor Cyan
Write-Host "                                          "
Write-Host "   Login:    admin / admin123             "
Write-Host "             reviewer / reviewer123       "
Write-Host "                                          "
Write-Host "   Press Ctrl+C to stop all services.     " -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`n[Stopping services...]" -ForegroundColor Yellow
    foreach ($job in $jobs) {
        Stop-Job -Job $job
        Remove-Job -Job $job
    }
    Write-Host "All services stopped." -ForegroundColor Green
}
