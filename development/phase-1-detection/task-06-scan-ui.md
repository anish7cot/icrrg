# Task 06 — Angular Scan Submission View

**Owner:** Frontend · **Est:** 1.5 hr

## Before You Start

- [x] Phase 0 frontend tasks done — Angular shell with Material is running
- [x] Task 05 (Scan API) is at least partially done — endpoint contract (request/response shape) is agreed
- [x] Proxy to backend is working

## Steps

- [x] Create scan submission component under `features/scan/scan-submit/`
- [x] Add a large textarea for pasting diff text
- [x] Add a "Scan" button that POSTs to `/api/v1/scans`
- [x] Show a loading spinner during API call
- [x] On success, navigate to the scan results view (or display inline)
- [x] On error, show a Material snackbar with the error message
- [x] Wire the route in `app.routes.ts`

## Challenges

- **Textarea needs to handle large diffs.** Use monospace font, allow horizontal scroll, and don't truncate. A diff can be hundreds of lines.
- **API might not be ready yet.** Mock the response shape and build against it. Swap to real API when backend is done. Don't block on each other.
- **Don't build a file upload widget.** Paste-in-textarea is enough for hackathon demo. File upload adds complexity for zero demo value.

## Done

- [x] User pastes diff, clicks Scan, sees loading state, gets results (or mock)

---
> **Note:** Mark all checklist items `[x]` after completing this task.
