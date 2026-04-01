# Task 05 — WebSocket Dashboard Updates

**Owner:** Backend · **Est:** 1 hr · **Priority:** P3 — Stretch goal

## Before You Start

- [x] Scan API stores results in DB
- [x] Angular dashboard exists from earlier phases

## Steps

- [x] Add WebSocket endpoint to FastAPI: `ws://localhost:8000/ws/scans`
- [x] When a new scan completes, broadcast a notification to connected WebSocket clients
- [x] Notification payload: scan_id, status, finding_count, timestamp
- [x] Test: open WebSocket client → submit a scan → receive notification

## Challenges

- **This is polish, not core.** If you're behind schedule, skip this entirely. Simple polling (frontend calls `GET /scans` every 5 seconds) works fine for a demo.
- **WebSocket + FastAPI** requires the `websockets` package. Install it if not already present.
- **One WebSocket bug can eat an hour.** Set a 30-minute timebox. If it's not working, fallback to polling.

## Done

- [x] WebSocket sends scan notifications to connected clients
- [x] (Fallback) Simple polling endpoint works as alternative

---
> **Note:** Mark all checklist items `[x]` after completing this task.
