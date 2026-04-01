# Task 07 — Database Schema + Alembic Migration

**Owner:** Backend · **Est:** 30 min

## Before You Start

- [x] Task 01 done — SQLAlchemy and Alembic installed
- [x] Task 03 done — `icrrg_dev` database exists and is accessible
- [x] Team agreed on initial tables: Scan, ScanFinding, Report

## Steps

- [x] Create `backend/app/db/models/base.py` — base model with id, created_at, updated_at
- [x] Create `Scan` model — id, repository, commit_hash, status, risk_score, created_at
- [x] Create `ScanFinding` model — id, scan_id (FK), finding_type, severity, message, file_path, line_number, confidence
- [x] Create `Report` model — id, repository, date_range_start, date_range_end, audience_type, content, created_at
- [x] Create `backend/app/db/session.py` — async engine + session factory
- [x] Run `alembic init alembic` inside `backend/`
- [x] Wire `alembic/env.py` to use async engine and model metadata
- [x] Generate migration: `alembic revision --autogenerate -m "initial schema"`
- [x] Apply: `alembic upgrade head`
- [x] Verify: `psql -d icrrg_dev -c "\dt"` shows tables

## Challenges

- **Alembic default `env.py` is sync.** You must modify it for async SQLAlchemy — search "alembic async" for the pattern. This trips up everyone the first time.
- **Connection string must use `postgresql+asyncpg://`**, not plain `postgresql://`
- **Only one person should own migrations** during the hackathon. Parallel migrations create branching heads that are painful to fix under time pressure.
- **Keep schema minimal.** Three tables are enough. Don't model future features.

## Done

- [x] `alembic upgrade head` succeeds
- [x] `\dt` in psql shows scans, scan_findings, reports tables

---
> **Note:** Mark all checklist items `[x]` after completing this task.
