# Task 06 — Angular Live Scan Feed

**Owner:** Frontend · **Est:** 1 hr

## Before You Start

- [x] Dashboard component exists
- [x] Scan API returns recent scans list
- [x] Task 05 (WebSocket) complete OR you're using polling

## Steps

- [x] Add a "Recent Scans" feed to the dashboard page
- [x] Show: timestamp, repository, commit hash (short), finding count, status (clean/issues found)
- [x] Auto-refresh: either WebSocket listener or simple 5-second polling on `GET /api/v1/scans`
- [x] New scans appear at the top of the feed
- [x] Click a scan to navigate to its detail view

## Challenges

- **Polling is fine for hackathon.** `setInterval` + HTTP GET every 5 seconds. Don't over-engineer.
- **During the live demo, this feed is your visual proof.** When the pre-commit hook blocks a commit, this feed should update simultaneously. Rehearse the timing.

## Done

- [x] Dashboard shows recent scans, auto-refreshes
- [x] ✅ PHASE 4 COMPLETE — money shot demoable

---
> **Note:** Mark all checklist items `[x]` after completing this task.
