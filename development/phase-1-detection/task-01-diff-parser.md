# Task 01 — Diff Parsing Service

**Owner:** Backend · **Est:** 1.5 hr

## Before You Start

- [x] Phase 0 complete — FastAPI running, DB connected
- [x] You understand unified diff format (`@@`, `+`, `-` lines)

## Steps

- [x] Create `backend/app/git/diff_parser.py`
- [x] Accept raw unified diff text as input
- [x] Parse into structured data: list of files, each with added/removed lines and line numbers
- [x] Handle multi-file diffs (a commit often touches multiple files)
- [x] Return a clean data structure (Pydantic model) that the detection engines can consume
- [x] Write 2–3 test cases with sample diffs

## Challenges

- **Diffs are messier than you think.** Binary files, renamed files, empty files — all produce diff lines that break naive parsers. For hackathon, focus on text file additions only. Skip binary diffs.
- **Line number math is off-by-one friendly.** The `@@` hunk header syntax (`@@ -a,b +c,d @@`) is 1-indexed. Get this wrong and every finding points to the wrong line.

## Done

- [x] Parser returns structured file + line data from a raw diff string

---
> **Note:** Mark all checklist items `[x]` after completing this task.
