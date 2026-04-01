# Task 02 — CLI Scan + Terminal Output

**Owner:** Backend · **Est:** 1.5 hr

## Before You Start

- [x] Task 01 (hook installer) works — hook fires on commit
- [x] Scan API is running

## Steps

- [x] Create `backend/cli/scanner.py` — takes diff text, calls scan API, returns results
- [x] Post the staged diff to `POST /api/v1/scans`
- [x] Parse the response and display findings in the terminal:
  - [x] Color-coded severity (red for Critical, yellow for High)
  - [x] File path and line number
  - [x] Short description of the finding
- [x] If no findings: print a green "✓ No issues found" message
- [x] If critical findings: print red block message and return exit code 1
- [x] Total scan time must complete under 2 seconds (PHI/secret detection only — no LLM in the commit path)

## Challenges

- **Terminal color output** differs between Windows (ANSI support limited) and Mac/Linux. Use the `colorama` library for cross-platform color support, or just use plain text symbols (✗, ✓).
- **The 2-second budget is real.** If the API is slow (cold start, DB connection pooling), the developer experience degrades immediately. Test the round-trip time.
- **Backend must be running for the hook to work.** If the developer hasn't started the backend, the hook fails with a connection error. Handle this gracefully — print "ICRRG backend not reachable, skipping scan" and allow the commit.

## Done

- [x] Hook fires → staged diff scanned → findings printed in terminal → commit blocked or allowed

---
> **Note:** Mark all checklist items `[x]` after completing this task.
