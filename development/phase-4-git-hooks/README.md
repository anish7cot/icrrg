# Phase 4 — Git Hook Integration (Hours 32–38)

End-to-end flow: `git commit` → hook fires → scan runs → commit blocked if dirty. Secrets never enter git history.

## Tasks

| # | Task | Owner | Est. |
|---|---|---|---|
| 01 | [Build CLI + pre-commit hook](task-01-cli-hook.md) | Backend / DevOps | 2h |
| 02 | [CLI scan + terminal output](task-02-cli-scan.md) | Backend | 1.5h |
| 03 | [Commit blocking logic](task-03-blocking.md) | Backend | 1h |
| 04 | [Edge cases: rebase, amend, merge](task-04-edge-cases.md) | Backend | 1h |
| 05 | [WebSocket dashboard updates](task-05-websocket.md) | Backend | 1h |
| 06 | [Angular live scan feed](task-06-live-feed.md) | Frontend | 1h |

## Exit Criteria

- [ ] Stage a file with a planted secret → `git commit` → commit BLOCKED
- [ ] `git log` shows NO trace of the secret
- [ ] Finding appears on dashboard simultaneously
