# Task 04 — Create Startup Script

**Owner:** DevOps / Backend · **Est:** 30 min

## Before You Start

- [x] Task 02 (FastAPI) and Task 03 (PostgreSQL + Redis) are complete
- [x] You know the start commands for each service on your OS

## Steps

- [x] Create `scripts/` directory at project root
- [x] Create `scripts/start_all.ps1` (Windows) that launches:
  - Backend: `cd backend; poetry run uvicorn app.main:app --reload --port 8000`
  - Frontend: `cd frontend; npm start` (skip gracefully if folder doesn't exist yet)
- [x] Create `scripts/start_all.sh` (Mac/Linux) with equivalent commands
- [x] Each service opens in its own terminal window so logs are visible
- [x] Script prints what it's starting before each launch
- [x] Test: run the script — backend comes up, frontend skipped with message if not yet created

## Challenges

- **PowerShell execution policy blocks .ps1 files** on fresh Windows installs. Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first.
- **Celery won't start yet** — the Celery app module doesn't exist until Phase 2. Script must skip it gracefully.
- **Don't try to start PostgreSQL/Redis from the script** if they run as OS services — just check they're running.

## Done

- [x] One command starts all available services
- [x] Missing services are skipped with a clear message

---
> **Note:** Mark all checklist items `[x]` after completing this task.
