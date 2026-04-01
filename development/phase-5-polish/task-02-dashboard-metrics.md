# Task 02 — Dashboard Metrics Page

**Owner:** Frontend · **Est:** 1.5 hr

## Before You Start

- [x] Scan results and review findings are stored in the database
- [x] API endpoint exists to return aggregate stats (or create a simple one)

## Steps

- [x] Create a dashboard landing page with metric cards:
  - Total scans run
  - Total issues found
  - Issues by severity (critical / high / medium / low)
  - Top issue types (e.g., "Hardcoded Secret", "SQL Injection")
- [x] Use Angular Material cards with large numbers and colored severity indicators
- [x] Pull data from `GET /api/v1/stats` (or aggregate client-side from scans list)
- [x] Make this the default route — judges see this first

## Challenges

- **Fake it if needed.** If the aggregation API isn't ready, compute stats client-side from the scans list. Don't block on backend.
- **Visual impact matters.** Big numbers, bold colors. Judges scan dashboards in 5 seconds.

## Done

- [x] Dashboard shows aggregate metrics, looks impressive at a glance

---
> **Note:** Mark all checklist items `[x]` after completing this task.
