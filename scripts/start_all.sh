#!/usr/bin/env bash
# start_all.sh — Launch all available services in separate terminal windows
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "\n${CYAN}=== Checking infrastructure ===${NC}"

# PostgreSQL
if command -v pg_isready &>/dev/null && pg_isready &>/dev/null; then
    echo -e "${GREEN}[OK] PostgreSQL is running${NC}"
else
    echo -e "${YELLOW}[SKIP] PostgreSQL is not running — start the service manually${NC}"
fi

# --- Start Backend ---
echo -e "\n${CYAN}=== Starting Backend ===${NC}"
if [ -f "$ROOT/backend/requirements.txt" ]; then
    echo "Launching FastAPI on port 8000..."
    (cd "$ROOT/backend" && source venv/bin/activate && uvicorn app.main:app --reload --port 8000) &
else
    echo -e "${YELLOW}[SKIP] backend/ not found — run Task 01 first${NC}"
fi

# --- Start Frontend ---
echo -e "\n${CYAN}=== Starting Frontend ===${NC}"
if [ -f "$ROOT/frontend/package.json" ]; then
    echo "Launching Angular on port 4200..."
    (cd "$ROOT/frontend" && npm start) &
else
    echo -e "${YELLOW}[SKIP] frontend/ not found — run Task 05 first${NC}"
fi

# --- Start Celery Worker ---
echo -e "\n${CYAN}=== Starting Celery Worker ===${NC}"
if [ -f "$ROOT/backend/app/celery_app.py" ]; then
    echo "Launching Celery worker..."
    (cd "$ROOT/backend" && source venv/bin/activate && celery -A app.celery_app worker --loglevel=info) &
else
    echo -e "${YELLOW}[SKIP] Celery app not found — available after Phase 2${NC}"
fi

echo -e "\n${CYAN}=== Done ===${NC}"
echo "Services launched in background. Use 'kill %N' or Ctrl+C to stop."
wait
