# Task 04 — Seed Demo Data

**Owner:** Everyone · **Est:** 1 hr

## Before You Start

- [ ] Database schema is final — no more migrations
- [ ] Scan and report APIs work end-to-end

## Steps

- [ ] Create a seed script (`scripts/seed_demo.py`) that inserts:
  - 15-20 commits across 2-3 fake repos
  - Mix of clean commits and ones with findings
  - At least 2 critical secrets, 3 PHI detections, 5 code review issues
  - 1-2 generated reports (different audiences)
- [ ] Run the seed script and verify dashboard shows rich data
- [ ] Keep one repo "clean" to show the happy path during demo

## Challenges

- **Don't demo with 2 commits.** Judges assume your tool only works at toy scale. 15+ commits shows credibility.
- **Make the data realistic.** Use real-looking repo names, commit messages, and file paths. "test123" kills the vibe.

## Done

- [ ] Database has 15+ commits with varied findings, dashboard looks populated

---
> **Note:** Mark all checklist items `[x]` after completing this task.
