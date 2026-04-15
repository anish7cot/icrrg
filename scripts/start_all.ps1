# start_all.ps1 - Launch all services in separate terminal windows
$root = Split-Path -Parent $PSScriptRoot

# --- Check infrastructure ---
Write-Host ""
Write-Host "=== Checking infrastructure ===" -ForegroundColor Cyan

# PostgreSQL
$null = & "C:\Program Files\PostgreSQL\17\bin\pg_isready" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] PostgreSQL is running" -ForegroundColor Green
} else {
    Write-Host "[SKIP] PostgreSQL is not running - start the service manually" -ForegroundColor Yellow
}

# --- Start Backend ---
Write-Host ""
Write-Host "=== Starting Backend ===" -ForegroundColor Cyan
$backendDir = Join-Path $root "backend"
if (Test-Path (Join-Path $backendDir "requirements.txt")) {
    Write-Host "Launching FastAPI on port 8000..."
    $venvActivate = Join-Path $backendDir "venv\Scripts\Activate.ps1"
    $cmd = "Set-Location -Path '$backendDir'; & '$venvActivate'; uvicorn app.main:app --reload --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
} else {
    Write-Host "[SKIP] backend/ not found - run Task 01 first" -ForegroundColor Yellow
}

# --- Start Frontend ---
Write-Host ""
Write-Host "=== Starting Frontend ===" -ForegroundColor Cyan
$frontendDir = Join-Path $root "frontend"
if (Test-Path (Join-Path $frontendDir "package.json")) {
    Write-Host "Launching Angular on port 4200..."
    $cmd = "Set-Location -Path '$frontendDir'; npx ng serve"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
} else {
    Write-Host "[SKIP] frontend/ not found - run Task 05 first" -ForegroundColor Yellow
}

# --- Start Celery Worker ---
Write-Host ""
Write-Host "=== Starting Celery Worker ===" -ForegroundColor Cyan
$celeryApp = Join-Path (Join-Path $backendDir "app") "tasks\celery_app.py"
if (Test-Path $celeryApp) {
    Write-Host "Launching Celery worker..."
    $venvActivate = Join-Path $backendDir "venv\Scripts\Activate.ps1"
    $cmd = "Set-Location -Path '$backendDir'; & '$venvActivate'; celery -A app.tasks.celery_app worker --loglevel=info --pool=solo"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
} else {
    Write-Host "[SKIP] Celery app not found - available after Phase 2" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "Services launched in separate windows. Close them individually to stop."
