# Task 03 — Code Review Pipeline

**Owner:** Backend / ML · **Est:** 2 hr

## Before You Start

- [x] Task 01 (prompt design) — prompt is tested in playground
- [x] Task 02 (LLM service) — provider wrapper works

## Steps

- [x] Create `backend/app/review/service.py` — orchestrates the full review pipeline
- [x] Pipeline: receive parsed diff → build prompt (system + few-shot + diff) → call LLM → parse response
- [x] Create `backend/app/review/response_parser.py` — validates LLM output against Pydantic model
- [x] Handle malformed LLM responses: if parsing fails, retry once, then return empty findings with error flag
- [x] Map LLM severity labels to your standard severity enum (Critical/High/Medium/Low)
- [x] Return findings in the same format as PHI/secret findings (unified results)
- [x] Test end-to-end: pass a diff with a SQL injection → get back a structured finding

## Challenges

- **LLM sometimes returns valid JSON wrapped in markdown code fences.** Strip ` ```json ` prefixes before parsing.
- **LLM might hallucinate line numbers.** Validate that reported line numbers exist in the diff. If they don't, flag the finding but mark line as "approximate."
- **Large diffs exceed context window.** If a diff is over ~3000 lines, split by file and review each file separately. Don't send the whole thing.

## Done

- [x] Pipeline returns structured review findings from a real diff via LLM

---
> **Note:** Mark all checklist items `[x]` after completing this task.
