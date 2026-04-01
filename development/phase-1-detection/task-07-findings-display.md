# Task 07 — Findings Display Component

**Owner:** Frontend · **Est:** 1.5 hr

## Before You Start

- [x] Task 06 (scan submission) exists — you need the scan result data to display
- [x] You have the API response shape (from backend or mocked)

## Steps

- [x] Create findings display component under `features/scan/scan-detail/`
- [x] Show each finding as a card with:
  - [x] Severity badge (Critical=red, High=orange, Medium=yellow, Low=blue)
  - [x] Finding type (Secret / PHI / Vulnerability)
  - [x] File path and line number
  - [x] Message / description
  - [x] Confidence score
- [x] Sort findings by severity (Critical first)
- [x] Show a summary at top: total findings count by severity
- [x] Use Material cards, chips, and color for visual clarity

## Challenges

- **Severity colors must be instantly readable.** Don't use subtle shades. Red = bad, green = good. Judges see your screen for seconds.
- **Empty state matters.** If a scan finds nothing, show a clear "No issues found ✓" message — not a blank screen.
- **Don't build inline diff highlighting yet.** A card list with file/line references is enough. Inline annotations are Phase 5 polish.

## Done

- [x] Findings render as color-coded cards sorted by severity
- [x] Empty state shows a clean "no issues" message

---
> **Note:** Mark all checklist items `[x]` after completing this task.
