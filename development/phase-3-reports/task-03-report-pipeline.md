# Task 03 — Report Generation Pipeline

**Owner:** Backend / ML · **Est:** 2 hr

## Before You Start

- [x] Task 01 (aggregation) returns structured data
- [x] Task 02 (prompt templates) are tested in playground
- [x] LLM service from Phase 2 Task 02 is working

## Steps

- [x] Create `backend/app/reports/service.py` — orchestrates report generation
- [x] Pipeline: receive config (date range, audience) → aggregate data → select template → build prompt → call LLM → parse response
- [x] LLM should return Markdown-formatted report with sections
- [x] Store generated report in the database (Report model)
- [x] Make this a Celery task (reports take 10–20 seconds to generate)
- [x] Update API: `POST /api/v1/reports` queues generation, `GET /api/v1/reports/{id}` fetches result

## Challenges

- **Report generation is slow** (large prompt + long output). Always async via Celery. Return a report ID immediately and let the frontend poll.
- **LLM might truncate long reports.** If the aggregated data is huge, the LLM runs out of output tokens. Summarize the input data rather than passing everything raw.
- **Mock provider needs report-mode responses too.** Add pre-written sample reports for each role in the mock provider.

## Done

- [x] Generate report for each role → stored in DB → retrievable via API

---
> **Note:** Mark all checklist items `[x]` after completing this task.
