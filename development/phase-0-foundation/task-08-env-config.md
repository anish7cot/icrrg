# Task 08 — Env Config + Gitignore

**Owner:** Everyone · **Est:** 15 min

## Before You Start

- [x] Connection strings from Task 03 are known
- [x] Team agreed on which OpenAI API key to use

## Steps

- [x] Create `.env.example` at project root with placeholder values:
  - `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `SECRET_KEY`, `CORS_ORIGINS`
- [x] Copy to `.env` and fill in real values
- [x] Create `.gitignore` covering: `.env`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`, `.angular/`, `*.pyc`
- [x] Verify: `git status` does NOT show `.env`
- [x] Confirm backend `config.py` reads from `.env` via Pydantic BaseSettings

## Challenges

- **Someone will accidentally commit `.env`.** If it happens, rotate the leaked key immediately — it's in git history forever.
- **Different `.env` values per machine** cause "works for me" bugs. Keep `.env.example` updated as the source of truth.

## Done

- [x] `.env` exists locally, is NOT in git
- [x] `.env.example` has all variable names documented

---
> **Note:** Mark all checklist items `[x]` after completing this task.
