# Phase 0 — Foundation (Hours 0–4)

Everyone can run the project locally. No features — just plumbing.

## Tasks

| # | Task | Owner | Est. |
|---|---|---|---|
| 01 | [Init Python project](task-01-init-python.md) | Backend Lead | 30m |
| 02 | [FastAPI skeleton](task-02-fastapi-skeleton.md) | Backend Lead | 30m |
| 03 | [Install PostgreSQL + Redis](task-03-postgres-redis.md) | DevOps | 45m |
| 04 | [Startup script](task-04-startup-script.md) | DevOps | 30m |
| 05 | [Init Angular project](task-05-init-angular.md) | Frontend Lead | 30m |
| 06 | [Angular Material shell](task-06-material-shell.md) | Frontend Lead | 45m |
| 07 | [Database schema + Alembic](task-07-db-schema.md) | Backend | 30m |
| 08 | [Env config + gitignore](task-08-env-config.md) | Everyone | 15m |
| 09 | [End-to-end verification](task-09-e2e-check.md) | Everyone | 15m |

## Exit Criteria

- [ ] Startup script launches all services
- [ ] Angular renders a landing page
- [ ] FastAPI `/health` returns 200
- [ ] PostgreSQL accepts queries
