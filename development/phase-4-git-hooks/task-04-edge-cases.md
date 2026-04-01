# Task 04 — Edge Cases: Rebase, Amend, Merge

**Owner:** Backend · **Est:** 1 hr

## Before You Start

- [x] Tasks 01–03 complete — basic hook flow works
- [x] You understand git internals: rebase replays commits, amend rewrites, merge combines

## Steps

- [x] Detect rebase: check for `GIT_REBASE_TODO` env var or `.git/rebase-merge/` directory → skip scan entirely
- [x] Detect merge: check for `.git/MERGE_HEAD` → skip scan (merged code was already committed elsewhere)
- [x] Handle amend: cache scan results by diff content hash → if diff hash matches a previous clean scan, skip re-scanning
- [x] Handle `git commit --no-verify`: can't prevent it, but log that a commit was made without scanning
- [x] Test each scenario manually

## Challenges

- **Rebase + hook = rage.** A 20-commit rebase triggers 20 hook calls. Without skip logic, this is 40+ seconds of scanning already-scanned code. Detect and skip.
- **`--no-verify` is unstoppable locally.** The Bitbucket webhook is the safety net. If a commit arrives without a scan record, the dashboard should show it as "unscanned."
- **Don't spend more than 1 hour here.** If edge cases are hard to test, get the basic skip logic in place and move on. These are P2 scenarios — the demo won't hit them.

## Done

- [x] Rebase doesn't trigger N redundant scans
- [x] Merge commits don't scan the entire merged branch
- [x] Amend uses cached results when diff is unchanged

---
> **Note:** Mark all checklist items `[x]` after completing this task.
