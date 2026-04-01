# Task 01 — Build CLI + Pre-Commit Hook Installer

**Owner:** Backend / DevOps · **Est:** 2 hr

## Before You Start

- [x] Scan API (`POST /api/v1/scans`) works from Phases 1–2
- [x] Git is installed on the demo machine
- [x] You understand how git hooks work (scripts in `.git/hooks/`)

## Steps

- [x] Create `backend/cli/main.py` — CLI entry point using `click` or `typer`
- [x] Create `backend/cli/hook_installer.py` — writes the pre-commit hook script to `.git/hooks/pre-commit`
- [x] The hook script should:
  - [x] Run `git diff --cached` to extract staged changes
  - [x] Pass the diff to the CLI scanner
  - [x] Exit 0 (allow commit) or exit 1 (block commit) based on scan results
- [x] CLI command: `icrrg install` — installs the hook in the current git repo
- [x] CLI command: `icrrg uninstall` — removes the hook
- [x] Make the hook script executable (important on Mac/Linux)
- [x] Test: `icrrg install` → make a commit → hook fires

## Challenges

- **Hook must use `git diff --cached`, not `git diff`.** `--cached` scans only staged changes. Without it, you scan the working tree which includes unstaged edits — produces wrong results.
- **Windows line endings in hook scripts** can break execution. Write the hook with LF line endings, not CRLF.
- **The hook runs in the repo's root directory.** Paths in the script must be absolute or resolved correctly. Don't assume the current directory.

## Done

- [x] `icrrg install` writes a working pre-commit hook
- [x] `git commit` triggers the hook

---
> **Note:** Mark all checklist items `[x]` after completing this task.
