# Task 07 — Prompt Tuning + Integration Testing

**Owner:** ML Lead · **Est:** 1.5 hr

## Before You Start

- [x] Full pipeline works: diff → API → detection + review → findings in UI
- [x] You have 3–4 test diffs with known vulnerabilities

## Steps

- [x] Test diff with SQL injection — verify detection + correct explanation
- [x] Test diff with XSS vulnerability — verify detection
- [x] Test diff with insecure deserialization or path traversal — verify detection
- [x] Test clean diff — verify NO false positives from the LLM
- [x] For any misses: adjust system prompt, add more specific instructions or few-shot examples
- [x] For false positives: add instructions to ignore style issues, focus on security
- [x] Run each test diff 3 times — output should be consistent across runs
- [x] Save tuned prompts as final versions

## Challenges

- **The LLM will want to be helpful and find SOMETHING.** Even in clean code, it may invent issues. Add explicit instruction: "If no security issues exist, return an empty findings array."
- **Output consistency across runs** is never 100%. Temperature=0 helps but doesn't guarantee identical output. Aim for structurally consistent (same findings found), not textually identical.
- **Know your demo diffs cold.** By end of this task, you should know exactly what the LLM will say for each demo input. Rehearse this.

## Done

- [x] 3+ vulnerability types reliably detected
- [x] Clean code returns zero findings
- [x] ✅ PHASE 2 COMPLETE — second demoable milestone

---
> **Note:** Mark all checklist items `[x]` after completing this task.
