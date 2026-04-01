# Task 04 — Angular Report Configuration Form

**Owner:** Frontend · **Est:** 1.5 hr

## Before You Start

- [x] Report API contract is agreed (POST body shape, response shape)
- [x] Angular Material is set up

## Steps

- [x] Create report config component under `features/reports/report-config/`
- [x] Form fields:
  - [x] Date range picker (start date, end date) — use Material datepicker
  - [x] Repository selector (dropdown or text input — keep simple)
  - [x] Audience toggle: Developer / Engineering Manager / Leadership — use Material button toggle group
- [x] "Generate Report" button that POSTs to `/api/v1/reports`
- [x] Show loading state while report generates
- [x] On completion, navigate to report preview view
- [x] Wire route in `app.routes.ts`

## Challenges

- **Material datepicker needs `MatNativeDateModule` or `MatMomentDateModule`.** Easy to forget, breaks at runtime.
- **Don't build a complex repo selector.** A text input where you type the repo name is fine. Dropdown with live search is Phase 5 polish.
- **The audience toggle is your demo moment.** Make it visually prominent — this is where judges see you switch between roles and get different reports.

## Done

- [x] Form submits config and triggers report generation

---
> **Note:** Mark all checklist items `[x]` after completing this task.
