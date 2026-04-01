# Task 02 — Regex Rule Engine for Secret Detection

**Owner:** ML / Backend · **Est:** 2 hr

## Before You Start

- [x] Task 01 (diff parser) is complete or in progress — you need the output format
- [x] You have a list of target patterns (AWS keys, generic passwords, tokens)

## Steps

- [x] Create `backend/app/detection/regex_engine.py`
- [x] Define pattern rules as a configurable list (pattern, label, severity)
- [x] Cover at minimum:
  - [x] AWS Access Key IDs (`AKIA...`)
  - [x] Generic API keys/tokens assigned to obvious variable names
  - [x] Connection strings with embedded passwords
  - [x] Private key headers (`BEGIN RSA PRIVATE KEY`)
  - [x] Common password variable assignments (`password = "..."`, `pwd`, `secret`)
- [x] Each match returns: matched text (redacted), line number, file path, confidence score, rule name
- [x] Create `backend/app/detection/rules/secrets.py` for rule definitions
- [x] Test with sample diffs containing planted secrets

## Challenges

- **False positives are the trust killer.** UUIDs, base64 config, test fixtures — all trigger naive patterns. Add basic context checks: skip matches in test files, `.example` files, and comments.
- **Regex greedy matching** can match huge chunks of a line. Use non-greedy quantifiers and anchor to variable assignment patterns.
- **Don't try to catch everything.** 10 solid rules with low false positives beat 50 noisy rules. You can always add more.

## Done

- [x] Engine flags AWS key, private key, and hardcoded password in test diff
- [x] Test fixtures and `.env.example` files are NOT flagged

---
> **Note:** Mark all checklist items `[x]` after completing this task.
