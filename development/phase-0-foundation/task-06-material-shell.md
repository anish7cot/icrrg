# Task 06 — Angular Material + Shell Layout

**Owner:** Frontend Lead · **Est:** 45 min

## Before You Start

- [x] Task 05 complete — `ng serve` runs
- [x] Decided on Material theme (just pick the default Indigo/Pink — move on)

## Steps

- [x] Run `ng add @angular/material` — pick prebuilt theme, enable animations
- [x] Create app shell layout:
  - [x] Top toolbar with app title "ICRRG"
  - [x] Sidenav with links: Dashboard, Scan, Reports
  - [x] `<router-outlet>` in the main content area
- [x] Add routes in `app.routes.ts` with placeholder components for each section
- [x] Verify: clicking nav links switches views

## Challenges

- **Material version must match Angular version** — `ng add` handles this, but manual install can mismatch
- **Don't burn time on responsive sidenav.** Use `mode="side"` (always visible). Mobile layout is Phase 5 polish at best.
- **Standalone routing** uses `provideRouter(routes)` in `app.config.ts` — no `RouterModule`

## Done

- [x] App shows toolbar + sidenav + placeholder content switching on nav click

---
> **Note:** Mark all checklist items `[x]` after completing this task.
