# Task 06 — Angular Code Review Results View

**Owner:** Frontend · **Est:** 2 hr

## Before You Start

- [x] Phase 1 findings display component exists — you're extending it
- [x] API response shape for code review findings is agreed

## Steps

- [x] Extend the scan detail view to show code review findings alongside detection findings
- [x] Group findings by file (accordion or collapsible sections)
- [x] Each finding card shows: severity, category (OWASP), issue summary, full explanation (expandable), remediation suggestion
- [x] Add a scan status indicator: "Detection complete ✓ — Code review in progress..." → "All reviews complete ✓"
- [x] Add a poll or refresh mechanism to update when async review finishes (simple polling is fine — don't build WebSocket yet)
- [x] Test with mock data if API isn't returning review findings yet

## Challenges

- **Async results mean the page needs to update.** A simple "Refresh" button or 5-second poll on `GET /scans/{id}` is enough. Don't over-engineer real-time for hackathon.
- **Code review explanations are long text.** Use expandable cards — show summary by default, full explanation on click. Don't wall-of-text the screen.
- **Visual distinction between detection and review findings** — use different icons or section headers so the demo clearly shows two engines working.

## Done

- [x] Detection + review findings display together, grouped by file
- [x] Status indicator shows when review is pending vs complete

---
> **Note:** Mark all checklist items `[x]` after completing this task.
