# Task 02 — FastAPI Skeleton with Health Check

**Owner:** Backend Lead · **Est:** 30 min

## Before You Start

- [x] Task 01 complete — `poetry install` succeeded
- [x] Virtual env activates (`poetry shell`)

## Steps

- [x] Create `backend/app/main.py` with FastAPI app instance
- [x] Add `GET /health` → returns `{"status": "healthy"}`
- [x] Add CORS middleware allowing `http://localhost:4200`
- [x] Create `backend/app/config.py` using Pydantic `BaseSettings`
- [x] Start server: `poetry run uvicorn app.main:app --reload --port 8000`
- [x] Hit `http://localhost:8000/health` — confirm 200
- [x] Hit `http://localhost:8000/docs` — confirm Swagger UI loads

## Challenges

- **Forget CORS = silent frontend failures.** Angular on port 4200 gets blocked. Add CORS middleware now, not "later."
- **Port 8000 conflict** with other services — agree on port assignments with team upfront

## Done

- [x] `/health` returns 200
- [x] `/docs` shows Swagger

---
> **Note:** Mark all checklist items `[x]` after completing this task.
