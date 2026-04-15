#!/usr/bin/env bash
# setup.sh — One-command project setup with prerequisite validation
# Usage: bash scripts/setup.sh
# Run from the project root directory.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; GRAY='\033[0;37m'; NC='\033[0m'

echo ""
echo -e "${CYAN}========================================"
echo "  ICRRG — Project Setup"
echo -e "========================================${NC}"
echo ""

ERRORS=()

# ── 1. Check Python ──────────────────────────────────────────────────
printf "Checking Python..."
PYTHON_CMD=""
for cmd in python3 python py; do
    if command -v "$cmd" &>/dev/null; then
        VER=$($cmd --version 2>&1)
        if echo "$VER" | grep -qE "Python 3\.(1[1-3])\."; then
            PYTHON_CMD="$cmd"
            echo -e " ${GREEN}OK ($VER)${NC}"
            break
        fi
    fi
done
if [ -z "$PYTHON_CMD" ]; then
    echo -e " ${RED}FAIL${NC}"
    ERRORS+=("Python 3.11-3.13 is required. Download from https://www.python.org/downloads/")
fi

# ── 2. Check Node.js ─────────────────────────────────────────────────
printf "Checking Node.js..."
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    NODE_MAJOR=$(echo "$NODE_VER" | sed 's/v\([0-9]*\).*/\1/')
    if [ "$NODE_MAJOR" -ge 18 ]; then
        echo -e " ${GREEN}OK ($NODE_VER)${NC}"
    else
        echo -e " ${RED}FAIL ($NODE_VER)${NC}"
        ERRORS+=("Node.js 18+ is required (found $NODE_VER). Download from https://nodejs.org/")
    fi
else
    echo -e " ${RED}FAIL${NC}"
    ERRORS+=("Node.js is not installed. Download from https://nodejs.org/")
fi

# ── 3. Check npm ─────────────────────────────────────────────────────
printf "Checking npm..."
if command -v npm &>/dev/null; then
    NPM_VER=$(npm --version)
    NPM_MAJOR=$(echo "$NPM_VER" | sed 's/\([0-9]*\).*/\1/')
    if [ "$NPM_MAJOR" -ge 9 ]; then
        echo -e " ${GREEN}OK (v$NPM_VER)${NC}"
    else
        echo -e " ${RED}FAIL (v$NPM_VER)${NC}"
        ERRORS+=("npm 9+ is required. Run: npm install -g npm@latest")
    fi
else
    echo -e " ${RED}FAIL${NC}"
    ERRORS+=("npm is not installed. It comes with Node.js.")
fi

# ── 4. Check PostgreSQL ──────────────────────────────────────────────
printf "Checking PostgreSQL..."
if command -v pg_isready &>/dev/null && pg_isready &>/dev/null; then
    echo -e " ${GREEN}OK (running)${NC}"
else
    echo -e " ${YELLOW}WARN (not running or not found)${NC}"
    echo -e "  ${YELLOW}-> Start PostgreSQL before running the backend.${NC}"
fi

# ── 5. Check Redis ───────────────────────────────────────────────────
printf "Checking Redis..."
if command -v redis-cli &>/dev/null; then
    PONG=$(redis-cli ping 2>/dev/null || echo "")
    if [ "$PONG" = "PONG" ]; then
        echo -e " ${GREEN}OK (running)${NC}"
    else
        echo -e " ${YELLOW}WARN (not responding)${NC}"
        echo -e "  ${YELLOW}-> Using cloud Redis from .env is also fine.${NC}"
    fi
else
    echo -e " ${YELLOW}SKIP (redis-cli not found — using cloud Redis is fine)${NC}"
fi

# ── Stop if critical errors ──────────────────────────────────────────
if [ ${#ERRORS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}SETUP BLOCKED — Fix these issues first:${NC}"
    for e in "${ERRORS[@]}"; do
        echo -e "  ${RED}✗ $e${NC}"
    done
    echo ""
    exit 1
fi

# ── 6. Setup Backend ─────────────────────────────────────────────────
echo ""
echo -e "${CYAN}--- Setting up Backend ---${NC}"

cd "$ROOT/backend"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "Installing CLI..."
pip install -e . --quiet

echo "Downloading spaCy model..."
$PYTHON_CMD -m spacy download en_core_web_sm --quiet 2>/dev/null || true

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}WARNING: No .env file found in backend/.${NC}"
    echo -e "${YELLOW}  Create one with DATABASE_URL, REDIS_URL, OPENAI_API_KEY, etc.${NC}"
else
    echo -e "${GREEN}.env file found.${NC}"
fi

echo "Running database migrations..."
alembic upgrade head 2>/dev/null && echo -e "${GREEN}Migrations complete.${NC}" || echo -e "${YELLOW}WARN: Migrations failed — check your DATABASE_URL in .env${NC}"

echo "Seeding admin user..."
$PYTHON_CMD seed_admin.py 2>/dev/null && echo -e "${GREEN}Admin user seeded.${NC}" || echo -e "${YELLOW}WARN: Seeding skipped (may already exist).${NC}"

# ── 7. Setup Frontend ────────────────────────────────────────────────
echo ""
echo -e "${CYAN}--- Setting up Frontend ---${NC}"

cd "$ROOT/frontend"
echo "Installing npm packages..."
npm install --legacy-peer-deps --quiet 2>/dev/null

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}========================================"
echo "  Setup Complete!"
echo -e "========================================${NC}"
echo ""
echo -e "${CYAN}To start the project, open 3 terminals:${NC}"
echo ""
echo -e "  Terminal 1 (Backend):"
echo -e "  ${GRAY}  cd backend && source venv/bin/activate${NC}"
echo -e "  ${GRAY}  uvicorn app.main:app --reload --port 8000${NC}"
echo ""
echo -e "  Terminal 2 (Celery):"
echo -e "  ${GRAY}  cd backend && source venv/bin/activate${NC}"
echo -e "  ${GRAY}  celery -A app.tasks.celery_app worker --loglevel=info${NC}"
echo ""
echo -e "  Terminal 3 (Frontend):"
echo -e "  ${GRAY}  cd frontend && npx ng serve${NC}"
echo ""
