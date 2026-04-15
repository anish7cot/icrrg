# setup.ps1 - One-command project setup with prerequisite validation
# Usage: .\scripts\setup.ps1
# Run from the project root directory.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ICRRG - Project Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$errors = @()

# -- 1. Check Python --
Write-Host "Checking Python..." -NoNewline
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -eq 3 -and $minor -ge 11) {
                $pythonCmd = $cmd
                Write-Host " OK ($ver)" -ForegroundColor Green
                break
            }
        }
    } catch {}
}
if (-not $pythonCmd) {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "Python 3.11+ is required. Download from https://www.python.org/downloads/"
}

# -- 2. Check Node.js --
Write-Host "Checking Node.js..." -NoNewline
try {
    $nodeVer = & node --version 2>&1
    if ($nodeVer -match "v(\d+)\.") {
        $nodeMajor = [int]$Matches[1]
        if ($nodeMajor -ge 18) {
            Write-Host " OK ($nodeVer)" -ForegroundColor Green
        } else {
            Write-Host " FAIL ($nodeVer)" -ForegroundColor Red
            $errors += "Node.js 18+ is required (found $nodeVer). Download from https://nodejs.org/"
        }
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "Node.js is not installed. Download from https://nodejs.org/"
}

# -- 3. Check npm --
Write-Host "Checking npm..." -NoNewline
try {
    $npmVer = & npm --version 2>&1
    if ($npmVer -match "^(\d+)\.") {
        $npmMajor = [int]$Matches[1]
        if ($npmMajor -ge 9) {
            Write-Host " OK (v$npmVer)" -ForegroundColor Green
        } else {
            Write-Host " FAIL (v$npmVer)" -ForegroundColor Red
            $errors += "npm 9+ is required (found $npmVer). Run: npm install -g npm@latest"
        }
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "npm is not installed. It comes with Node.js."
}

# -- 4. Check PostgreSQL --
Write-Host "Checking PostgreSQL..." -NoNewline
$pgReady = $false
foreach ($pgPath in @(
    "pg_isready",
    "C:\Program Files\PostgreSQL\17\bin\pg_isready",
    "C:\Program Files\PostgreSQL\16\bin\pg_isready",
    "C:\Program Files\PostgreSQL\15\bin\pg_isready"
)) {
    try {
        $null = & $pgPath 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pgReady = $true
            Write-Host " OK (running)" -ForegroundColor Green
            break
        }
    } catch {}
}
if (-not $pgReady) {
    Write-Host " WARN (not running or not found)" -ForegroundColor Yellow
    Write-Host "  -> Start PostgreSQL before running the backend." -ForegroundColor Yellow
}

# -- 5. Check Redis --
Write-Host "Checking Redis..." -NoNewline
try {
    $redisResp = & redis-cli ping 2>$null
    if ($redisResp -eq "PONG") {
        Write-Host " OK (running)" -ForegroundColor Green
    } else {
        Write-Host " WARN (not responding)" -ForegroundColor Yellow
        Write-Host "  -> Using cloud Redis from .env is also fine." -ForegroundColor Yellow
    }
} catch {
    Write-Host " SKIP (redis-cli not found, using cloud Redis is fine)" -ForegroundColor Yellow
}

# -- Stop if critical errors --
if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "SETUP BLOCKED - Fix these issues first:" -ForegroundColor Red
    foreach ($e in $errors) {
        Write-Host "  X $e" -ForegroundColor Red
    }
    Write-Host ""
    exit 1
}

# -- 6. Setup Backend --
Write-Host ""
Write-Host "--- Setting up Backend ---" -ForegroundColor Cyan

$backendDir = Join-Path $root "backend"
Push-Location $backendDir

# Create venv if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    & $pythonCmd -m venv venv
}

# Activate venv
Write-Host "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing Python dependencies..."
pip install -r requirements.txt --quiet
pip install -e . --quiet

# Download spaCy model
Write-Host "Downloading spaCy model..."
try {
    & $pythonCmd -m spacy download en_core_web_sm --quiet 2>&1 | Out-Null
    Write-Host "spaCy model installed." -ForegroundColor Green
} catch {
    Write-Host "WARN: spaCy model download had issues, may already be installed." -ForegroundColor Yellow
}

# Check for .env, auto-copy from .env.example if missing
if (-not (Test-Path ".env")) {
    $envExample = Join-Path $root ".env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample ".env"
        Write-Host ".env created from .env.example - update it with your credentials." -ForegroundColor Yellow
    } else {
        Write-Host "WARNING: No .env file found. Create one with DATABASE_URL, REDIS_URL, etc." -ForegroundColor Yellow
    }
} else {
    Write-Host ".env file found." -ForegroundColor Green
}

# Run migrations
Write-Host "Running database migrations..."
try {
    alembic upgrade head 2>$null
    Write-Host "Migrations complete." -ForegroundColor Green
} catch {
    Write-Host "WARN: Migrations failed - check your DATABASE_URL in .env" -ForegroundColor Yellow
}

# Seed admin
Write-Host "Seeding admin user..."
try {
    & $pythonCmd seed_admin.py 2>$null
    Write-Host "Admin user seeded." -ForegroundColor Green
} catch {
    Write-Host "WARN: Seeding skipped (may already exist)." -ForegroundColor Yellow
}

Pop-Location

# -- 7. Setup Frontend --
Write-Host ""
Write-Host "--- Setting up Frontend ---" -ForegroundColor Cyan

$frontendDir = Join-Path $root "frontend"
Push-Location $frontendDir

Write-Host "Installing npm packages..."
try {
    npm install --legacy-peer-deps --quiet 2>&1 | Out-Null
    Write-Host "npm packages installed." -ForegroundColor Green
} catch {
    Write-Host "WARN: npm install had warnings, packages may still be installed." -ForegroundColor Yellow
}

Pop-Location

# -- Done --
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the project, open 3 terminals:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Terminal 1 (Backend):" -ForegroundColor White
Write-Host "    cd backend" -ForegroundColor Gray
Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "    uvicorn app.main:app --reload --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "  Terminal 2 (Celery):" -ForegroundColor White
Write-Host "    cd backend" -ForegroundColor Gray
Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "    celery -A app.tasks.celery_app worker --loglevel=info --pool=solo" -ForegroundColor Gray
Write-Host ""
Write-Host "  Terminal 3 (Frontend):" -ForegroundColor White
Write-Host "    cd frontend" -ForegroundColor Gray
Write-Host "    npx ng serve" -ForegroundColor Gray
Write-Host ""
