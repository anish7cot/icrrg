# Task 05 — Scan API Endpoint

**Owner:** Backend Lead · **Est:** 1.5 hr

## Before You Start

- [x] Tasks 01–04 (diff parser + detection engines) are complete or testable
- [x] Database schema from Phase 0 Task 07 is migrated
- [x] FastAPI skeleton is running

## Steps

- [x] Create `backend/app/api/v1/scans.py`
- [x] Implement `POST /api/v1/scans` — accepts raw diff text in request body
- [x] Wire the endpoint to the detection pipeline: parse diff → run regex → run entropy → run NER
- [x] Aggregate all findings, assign severity scores
- [x] Store scan + findings in the database
- [x] Return scan results as JSON response with findings array
- [x] Implement `GET /api/v1/scans/{id}` to retrieve a past scan
- [x] Test via Swagger UI: paste a diff, get findings back

## Challenges

- **Keep this endpoint synchronous for now.** PHI/secret detection is fast (under 2 seconds). Don't add Celery complexity here — that's Phase 2 for LLM calls.
- **Request body size.** Large diffs can be several MB. Set a reasonable limit (5 MB for hackathon) and return 413 if exceeded.
- **Pydantic response model** is your contract with the frontend. Define it clearly — the frontend dev will build against it.

## Done

- [x] POST diff to `/api/v1/scans` → returns findings JSON
- [x] Findings are stored in the database

---
> **Note:** Mark all checklist items `[x]` after completing this task.
