# Task 05 — Report Preview Component

**Owner:** Frontend · **Est:** 2 hr

## Before You Start

- [x] Task 04 (config form) exists
- [x] Report API returns Markdown content

## Steps

- [x] Create report preview component under `features/reports/report-preview/`
- [x] Render Markdown content as formatted HTML (use a Markdown rendering library like `ngx-markdown` or `marked`)
- [x] Show report metadata at top: date range, audience type, generated timestamp
- [x] Add "Export" button (Markdown download as `.md` file — simplest option)
- [x] Add poll for report status (if report is still generating, show progress indicator)
- [x] Test with a real generated report

## Challenges

- **Markdown rendering library choice.** `ngx-markdown` is the easiest for Angular. Install it, import it, pipe your content through. Don't build a custom renderer.
- **LLM Markdown quality varies.** Sometimes headings are inconsistent, lists are malformed. Basic CSS styling for the rendered output smooths over rough edges.
- **Keep the preview read-only.** Don't build an editor. Show the report, offer export. That's it.

## Done

- [x] Generated report renders as formatted, readable content
- [x] Export downloads as `.md` file

---
> **Note:** Mark all checklist items `[x]` after completing this task.
