# Task 03 — Install PostgreSQL + Redis Locally

**Owner:** DevOps / Backend · **Est:** 45 min

## Before You Start

- [x] Admin/sudo access on your machine
- [x] Team agreed on DB name, user, password (keep it simple: `icrrg_dev` / `postgres` / `postgres`)

## Steps

### PostgreSQL
- [x] Install PostgreSQL 15+ (PostgreSQL 17 already installed)
  - Windows: EDB installer from postgresql.org
  - macOS: `brew install postgresql@15 && brew services start postgresql@15`
  - Linux: `sudo apt install postgresql-15`
- [x] Verify running: `pg_isready`
- [x] Create database: `createdb icrrg_dev`
- [x] Test: `psql -d icrrg_dev -c "SELECT 1;"`

### Redis
- [x] Install Redis (using Redis Cloud free tier instead of local install)
  - Windows: Install Memurai from memurai.com (native Redis alternative)
  - macOS: `brew install redis && brew services start redis`
  - Linux: `sudo apt install redis-server`
- [x] Verify: `redis-cli ping` → `PONG` (verified via Python `redis.ping()` → True)

### Record
- [x] Note connection strings for `.env`:
  - `DATABASE_URL=postgresql+asyncpg://postgres:hdr%40123@localhost:5432/icrrg_dev`
  - `REDIS_URL=redis://default:***@redis-16894.c245.us-east-1-3.ec2.cloud.redislabs.com:16894`

## Challenges

- **Windows has no native Redis.** Memurai is the pragmatic fix. If it fails, use Redis inside WSL2.
- **Port 5432 already taken** by an older PostgreSQL install — stop the old service or use a different port
- **Linux `peer` auth** blocks password login by default. Either connect as OS user `postgres` or edit `pg_hba.conf` to use `md5`.

## Done

- [x] `pg_isready` says "accepting connections"
- [x] `redis-cli ping` says `PONG` (via Python redis.ping())

---
> **Note:** Mark all checklist items `[x]` after completing this task.
