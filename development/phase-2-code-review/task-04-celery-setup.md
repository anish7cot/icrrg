# Task 04 — Celery Async Task Setup

**Owner:** Backend · **Est:** 1 hr

## Before You Start

- [x] Redis is running (from Phase 0 Task 03)
- [x] Celery is installed (from Phase 0 Task 01)
- [x] Task 03 (review pipeline) works synchronously

## Steps

- [x] Create `backend/app/tasks/celery_app.py` — configure Celery with Redis as broker
- [x] Create `backend/app/tasks/review_task.py` — wraps the review pipeline as a Celery task
- [x] Task accepts scan_id, fetches diff from DB, runs review, stores findings in DB
- [x] Update the scan API endpoint: after sync PHI/secret detection, queue the async code review task
- [x] Return scan response immediately (PHI/secret results), mark code review as "pending"
- [x] Start Celery worker: `celery -A app.tasks.celery_app worker --loglevel=info`
- [x] Test: submit a scan, see PHI results immediately, code review findings appear in DB after a few seconds

## Challenges

- **Celery worker is a separate process.** It must have access to the same code, config, and database. If you change code, restart the worker.
- **Forgetting to start the Celery worker** is the #1 reason async tasks silently disappear. Add it to the startup script.
- **Don't make the hackathon Celery setup complex.** Single worker, single queue, no routing. Keep it simple.

## Done

- [x] Code review runs in background via Celery
- [x] Scan API returns PHI/secret results immediately, review results appear later

---
> **Note:** Mark all checklist items `[x]` after completing this task.
