# Task 03 — Entropy Analysis for Secret Detection

**Owner:** ML / Backend · **Est:** 1.5 hr

## Before You Start

- [x] Task 02 (regex engine) is complete or in progress
- [x] You understand Shannon entropy (measures randomness of a string)

## Steps

- [x] Create `backend/app/detection/entropy.py`
- [x] Implement Shannon entropy calculator for strings
- [x] Scan added lines in diffs for high-entropy substrings (threshold: ~4.5 for hex, ~5.0 for base64)
- [x] Only flag high-entropy strings that appear in suspicious contexts (assigned to variables like `key`, `secret`, `token`, `password`, `api_key`)
- [x] Return findings with: string (truncated/redacted), entropy score, line number, file path
- [x] Test with known secrets vs normal code strings

## Challenges

- **High entropy alone is meaningless.** UUIDs, hashes, and encoded data are high-entropy but not secrets. Without context filtering, you'll flag half the codebase. Always pair with variable name analysis.
- **Threshold tuning** — too low catches everything, too high misses real secrets. Start conservative (5.0), lower if you're missing things during testing.
- **Don't over-invest here.** Regex catches the obvious stuff. Entropy is a complement, not the star of the demo.

## Done

- [x] Catches a random API key assigned to `api_key = "a8f3..."` that regex missed
- [x] Does NOT flag UUIDs or hash constants

---
> **Note:** Mark all checklist items `[x]` after completing this task.
