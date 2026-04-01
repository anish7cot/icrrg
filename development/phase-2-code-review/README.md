# Phase 2 — Intelligent Code Review (Hours 14–22)

LLM-powered security and quality review on commit diffs.

## Tasks

| # | Task | Owner | Est. |
|---|---|---|---|
| 01 | [Design code review prompt](task-01-review-prompt.md) | ML Lead | 2h |
| 02 | [LLM service wrapper](task-02-llm-service.md) | Backend | 1.5h |
| 03 | [Code review pipeline](task-03-review-pipeline.md) | Backend / ML | 2h |
| 04 | [Celery async task setup](task-04-celery-setup.md) | Backend | 1h |
| 05 | [Store review findings](task-05-store-findings.md) | Backend | 1h |
| 06 | [Angular review results view](task-06-review-ui.md) | Frontend | 2h |
| 07 | [Prompt tuning + testing](task-07-prompt-tuning.md) | ML Lead | 1.5h |

## Exit Criteria

- [ ] Submit diff with SQL injection + insecure deserialization
- [ ] System identifies both, explains why, suggests fix
- [ ] Results display in Angular with severity grouping
