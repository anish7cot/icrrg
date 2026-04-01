# Task 06 — PDF/Markdown Export

**Owner:** Frontend / Backend · **Est:** 1.5 hr · **Priority:** P3 — Stretch goal

## Before You Start

- [x] Task 05 (report preview) is working
- [x] Markdown export already works from Task 05

## Steps

- [x] Markdown export: create a Blob from report content and trigger browser download — should already work from Task 05
- [x] PDF export (if time permits):
  - [x] Option A (simple): use browser `window.print()` on the report preview — styled for print via CSS
  - [ ] Option B (backend): use WeasyPrint or reportlab in Python to convert Markdown → PDF via an endpoint
- [x] Test: export both formats, verify they're readable

## Challenges

- **PDF generation is a time sink.** `window.print()` with print CSS is a 15-minute solution. WeasyPrint backend is a 2-hour rabbit hole. Choose wisely under time pressure.
- **This is P3 — cut it if you're behind.** A Markdown download is enough. No judge has ever said "I loved the project but there was no PDF button."

## Done

- [x] Markdown export works
- [x] (Stretch) PDF export works

---
> **Note:** Mark all checklist items `[x]` after completing this task.
