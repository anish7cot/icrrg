# Task 05 — Initialize Angular Project

**Owner:** Frontend Lead · **Est:** 30 min

## Before You Start

- [x] Node.js 20 LTS installed (`node --version`)
- [x] Angular CLI 17+ installed (`ng version`)
- [x] Task 02 done — backend running on port 8000

## Steps

- [x] Run `ng new frontend --routing --style=scss --standalone` from project root
- [x] Verify `cd frontend && ng serve` works at `http://localhost:4200`
- [x] Create `frontend/src/proxy.conf.json` proxying `/api/*` to `http://localhost:8000`
- [x] Update `angular.json` serve target to use the proxy config
- [x] Test proxy: browser at `http://localhost:4200/api/v1/` returns backend response
- [x] Remove default boilerplate from `app.component.html`

## Challenges

- **Proxy config only works with `ng serve`**, not production builds. That's fine for hackathon.
- **Angular CLI version differences** across team members generate different project structures — agree on CLI version
- **`--standalone` changes how routing works** — uses `provideRouter()` in `app.config.ts`, not `RouterModule.forRoot()`

## Done

- [x] `http://localhost:4200` loads Angular app
- [x] `/api/` proxy reaches FastAPI backend

---
> **Note:** Mark all checklist items `[x]` after completing this task.
