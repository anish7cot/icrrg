# Task 01 — Init Python Project with Poetry

**Owner:** Backend Lead · **Est:** 30 min

## Before You Start

- [x] Python 3.11+ installed (`python --version`)
- [x] Poetry installed (`poetry --version`)
- [ ] Git repo initialized

## Steps

- [x] Create `backend/` directory
- [x] Run `poetry init` inside `backend/`, set Python `>=3.11,<3.13`
- [x] Add deps: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic`, `pydantic-settings`, `python-dotenv`
- [x] Add ML deps: `openai`, `spacy`, `scikit-learn`
- [x] Add queue deps: `celery[redis]`, `redis`
- [x] Add dev deps: `pytest`, `httpx`
- [x] Run `poetry install` — must complete with no errors
- [x] Create `backend/app/__init__.py`
- [x] Download spaCy model: `poetry run python -m spacy download en_core_web_sm`

## Challenges

- **spaCy model download is separate** from `poetry install` — easy to forget, breaks NER pipeline later
- **Poetry lockfile version conflicts** if team members have different Poetry versions — agree on one version
- **Python 3.10 won't cut it** — some async SQLAlchemy features need 3.11+

## Done

- [x] `poetry run python -c "import fastapi; print('ok')"` prints `ok`

---
> **Note:** Mark all checklist items `[x]` after completing this task.
