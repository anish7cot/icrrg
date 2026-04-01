# Task 05 — End-to-End Testing

**Owner:** Everyone · **Est:** 1 hr

## Before You Start

- [ ] All features from Phases 1–4 are integrated
- [ ] Demo data is seeded (Task 04)

## Steps

- [ ] Run through the full demo flow 3 times:
  1. Open dashboard → show metrics
  2. Paste a diff with a planted secret → show findings
  3. Submit a code review → show LLM findings
  4. Generate a report → show output
  5. Attempt a git commit with a secret → show blocked commit
- [ ] Fix any bugs found during the run-throughs
- [ ] Test on a clean machine if possible (or fresh terminal/browser)
- [ ] Verify startup script launches everything correctly from scratch

## Challenges

- **First-run bugs.** Things break when someone other than the developer runs them. Test the startup script on a teammate's machine.
- **API key expiry / rate limits.** Confirm your OpenAI key has enough credits for the demo + 3 rehearsals.

## Done

- [ ] Full demo flow works 3 times in a row without errors

---
> **Note:** Mark all checklist items `[x]` after completing this task.
