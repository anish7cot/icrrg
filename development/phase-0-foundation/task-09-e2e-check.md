# Task 09 — End-to-End Verification

**Owner:** Everyone · **Est:** 15 min

## Before You Start

- [x] ALL Phase 0 tasks (01–08) are complete
- [x] All services are running

## Steps

- [x] Open Angular app at `http://localhost:4200` — page loads
- [x] Angular calls backend through proxy — `/api/v1/` returns data
- [x] FastAPI `/health` returns 200
- [x] FastAPI can query the database (create a quick test endpoint or verify in Swagger)
- [x] Redis is reachable (`redis-cli ping`)
- [ ] Every team member clones the repo and runs the startup script successfully

## Challenges

- **"It works on my machine" is the number one hackathon killer.** Every team member must run this check. If it fails for anyone, fix it now — not at hour 30.
- **Proxy misconfiguration** silently returns 404s or CORS errors. Check browser DevTools network tab.

## Done

- [ ] Full stack runs on every team member's machine
- [x] ✅ PHASE 0 COMPLETE — proceed to Phase 1

---
> **Note:** Mark all checklist items `[x]` after completing this task.
