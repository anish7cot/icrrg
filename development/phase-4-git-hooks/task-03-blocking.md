# Task 03 — Commit Blocking Logic

**Owner:** Backend · **Est:** 1 hr

## Before You Start

- [x] Task 02 (CLI scan) returns findings to terminal
- [x] Exit codes work: 0 = allow, 1 = block

## Steps

- [x] Implement configurable severity threshold for blocking:
  - [x] Critical → always block
  - [x] High → block by default, configurable to warn-only
  - [x] Medium → warn (print but allow commit)
  - [x] Low → info only
- [x] Read threshold from a config file (`.icrrg.yml` in repo root) or use sensible defaults
- [x] Terminal output clearly states: "COMMIT BLOCKED: 2 critical findings" or "WARNING: 1 high-severity finding (commit allowed)"
- [x] Test with each severity level — verify block/allow behavior

## Challenges

- **Developers will hate hard blocks on Medium.** Default to blocking only Critical. Let teams configure tighter thresholds if they want.
- **Keep the config file optional.** If `.icrrg.yml` doesn't exist, use defaults. Don't force config file creation to use the tool.
- **Demo tip:** For the live demo, plant a Critical finding so the block is dramatic. Then fix it, re-commit, and show the green "✓" flow.

## Done

- [x] Critical findings block the commit
- [x] Warning findings print but allow commit
- [x] Threshold is configurable

---
> **Note:** Mark all checklist items `[x]` after completing this task.
