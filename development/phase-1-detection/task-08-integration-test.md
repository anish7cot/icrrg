# Task 08 — Integration Test with Planted Secrets + PHI

**Owner:** Everyone · **Est:** 1 hr

## Before You Start

- [x] Tasks 01–07 are all complete
- [x] Full pipeline works: paste diff → API → findings → UI display

## Steps

- [x] Create test diff #1: contains a hardcoded AWS key (`AKIAIOSFODNN7EXAMPLE`)
- [x] Create test diff #2: contains a patient SSN (`123-45-6789`) near patient context keywords
- [x] Create test diff #3: contains a database connection string with embedded password
- [x] Create test diff #4: clean code with no issues — should return zero findings
- [x] Run each through the full pipeline (UI → API → detection → display)
- [x] Verify: correct findings, correct severity, correct file/line references
- [x] Fix any false positives or missed detections found during testing
- [x] Save the working test diffs in `backend/tests/fixtures/sample_diffs/` for reuse in demo

## Challenges

- **False positives will emerge now.** This is expected. Tune regex rules and NER context filtering based on what you find. Budget time for iteration.
- **Test diff #4 (clean code) is critical.** If the tool flags clean code, the demo loses credibility. Zero findings must produce a clean result.
- **Save these exact diffs.** They become your demo scripts. You'll use the same inputs on stage.

## Done

- [x] All 4 test diffs produce correct results through the full pipeline
- [x] Test diffs saved for demo reuse
- [x] ✅ PHASE 1 COMPLETE — first demoable milestone

---
> **Note:** Mark all checklist items `[x]` after completing this task.
