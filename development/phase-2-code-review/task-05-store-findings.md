# Task 05 — Store Review Findings in Results Engine

**Owner:** Backend · **Est:** 1 hr

## Before You Start

- [x] Task 04 (Celery) is working — review task runs in background
- [x] ScanFinding model from Phase 0 supports a `finding_type` field

## Steps

- [x] Ensure `ScanFinding` model can store code review findings (finding_type = "vulnerability")
- [x] When Celery review task completes, save each finding to the database linked to the scan
- [x] Update scan status from "pending_review" to "complete" after review finishes
- [x] Update `GET /api/v1/scans/{id}` to include both detection AND review findings
- [x] Add a composite risk score to the scan (aggregate of all finding severities)
- [x] Test: fetch a completed scan — response includes both PHI/secret and code review findings

## Challenges

- **Race condition**: frontend might fetch the scan before the review task finishes. Return what's available with a status field ("detection_complete", "review_pending", "complete").
- **Don't create a separate model for review findings.** Reuse `ScanFinding` with a type discriminator. One table, one query, one response.

## Done

- [x] Both detection and review findings stored in same table
- [x] `GET /scans/{id}` returns unified findings with scan status

---
> **Note:** Mark all checklist items `[x]` after completing this task.
