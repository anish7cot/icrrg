# ICRRG — Short-Term Enhancement Plan (1–2 Sprints)

> **Target Timeline:** 2–4 weeks  
> **Scope:** High-impact features that build on existing infrastructure with moderate effort.

---

## 1. WebSocket Frontend Integration

### Problem
The backend already exposes a WebSocket endpoint at `ws://localhost:8000/ws/scans` that broadcasts scan completion events, but the Angular frontend does not consume it. The dashboard currently uses REST polling (`GET /api/v1/scans/notifications`) which introduces latency and unnecessary network overhead.

### Proposed Solution
- Create a `WebSocketService` in `frontend/src/app/services/websocket.service.ts` that manages a persistent WebSocket connection.
- Auto-reconnect on disconnect with exponential backoff.
- Parse incoming messages (scan_id, status, finding_count, timestamp) and expose them as an RxJS `Observable`.
- Integrate into `DashboardComponent` to update metrics and the scan list in real time without manual refresh.
- Add a visual indicator (e.g., a green dot) showing live connection status.

### Acceptance Criteria
- [ ] Dashboard updates within 1 second of scan completion (no page refresh).
- [ ] Connection auto-reconnects after network interruption.
- [ ] Falls back to REST polling if WebSocket is unavailable.

### Estimated Effort: 3–4 hours

---

## 2. PDF Report Export

### Problem
Reports are generated only in Markdown format. Stakeholders (especially leadership) expect downloadable, professionally formatted PDF documents for compliance evidence and executive reviews.

### Proposed Solution
- Add a server-side PDF generation endpoint: `GET /api/v1/reports/{id}/export?format=pdf`.
- Use **WeasyPrint** (Python library) to convert the existing Markdown report content → HTML (via `markdown` library) → PDF with styled CSS.
- Include a cover page with: report title, audience type, date range, generation timestamp, and repository name.
- Add a "Download PDF" button on the `ReportViewComponent` in the frontend.
- Optional: Support DOCX export via `python-docx` as a secondary format.

### Acceptance Criteria
- [ ] PDF renders cleanly with proper headings, tables, and severity color-coding.
- [ ] File size is reasonable (< 2 MB for a typical report).
- [ ] Download works from the frontend with a single click.

### Estimated Effort: 4–6 hours

### Dependencies
- `pip install weasyprint markdown`
- WeasyPrint requires system libraries (Cairo, Pango) — document in quick-start guide.

---

## 3. Context-Aware False Positive Classifier

### Problem
The current detection engines (regex, entropy, NER) produce false positives — for example, high-entropy strings that are hash constants, example API keys in documentation, or test fixture data. The architecture specifies a "Layer 4 Context-Aware Classification" module that does not yet exist.

### Proposed Solution
- Create `backend/app/detection/context_classifier.py`.
- Implement a scoring model that evaluates each finding against contextual signals:
  - **File context:** Is it a test file, example config, documentation, or migration?
  - **Line context:** Is the matched string in a comment, a constant declaration, an import, or a variable assignment?
  - **Code pattern:** Does the surrounding code suggest a placeholder (e.g., `"CHANGE_ME"`, `"xxx"`, `os.environ.get()`)?
  - **Historical context:** Has this exact string been previously suppressed/allowed by the user?
- Assign a `false_positive_probability` score (0.0–1.0) to each finding.
- Findings with score > 0.8 are auto-suppressed (but still stored with `suppressed=true` flag).
- Findings with score 0.5–0.8 are flagged as "likely false positive" in the UI.

### Acceptance Criteria
- [ ] False positive rate on test fixtures drops by at least 40%.
- [ ] No true positives are suppressed (validated against a curated test set).
- [ ] Suppressed findings are still queryable via API with `?include_suppressed=true`.

### Estimated Effort: 8–12 hours

---

## 4. Dependency Vulnerability Scanning

### Problem
ICRRG scans code content for secrets and vulnerabilities but ignores the supply chain. If a developer adds a dependency with a known CVE (e.g., `log4j 2.14.1`), the current system has no way to flag it.

### Proposed Solution
- Create `backend/app/detection/dependency_scanner.py`.
- Parse dependency manifest files from diffs:
  - Python: `requirements.txt`, `pyproject.toml`, `Pipfile`
  - JavaScript: `package.json`, `yarn.lock`, `pnpm-lock.yaml`
  - Java: `pom.xml`, `build.gradle`
  - Go: `go.mod`
  - Ruby: `Gemfile`
- For each added or updated dependency, query the **OSV (Open Source Vulnerabilities)** API (`https://api.osv.dev/v1/query`) for known CVEs.
- Return findings with severity mapped from CVSS score: CRITICAL (9.0+), HIGH (7.0–8.9), MEDIUM (4.0–6.9), LOW (0.1–3.9).
- Integrate into the scan pipeline alongside regex/entropy/NER detection.

### Acceptance Criteria
- [ ] Detects known CVEs in added/updated Python and JavaScript dependencies.
- [ ] Findings include CVE ID, severity, affected version range, and a link to the advisory.
- [ ] Scan time increase is < 2 seconds (OSV API calls are batched).

### Estimated Effort: 10–14 hours

### Dependencies
- OSV API is free and requires no authentication.
- Consider caching responses in Redis (TTL: 24 hours) to avoid redundant lookups.

---

## 5. Slack / Microsoft Teams Notifications

### Problem
When a critical finding is detected, the only way to know is to check the dashboard or CLI output. Engineering managers and security leads need proactive alerts in their communication channels.

### Proposed Solution
- Create `backend/app/notifications/` module with:
  - `slack.py` — sends messages via Slack Incoming Webhooks.
  - `teams.py` — sends Adaptive Cards via MS Teams Incoming Webhooks.
  - `dispatcher.py` — routes notifications based on severity thresholds and channel config.
- Add configuration in `.env`:
  ```
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
  TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
  NOTIFY_MIN_SEVERITY=high    # Only notify for HIGH and CRITICAL
  ```
- Trigger notifications at scan completion (in the Celery task or post-scan hook).
- Message format includes: repository name, commit hash, finding count by severity, top 3 findings, and a link to the dashboard.

### Acceptance Criteria
- [ ] Slack notification arrives within 30 seconds of scan completion.
- [ ] Teams notification renders as a formatted Adaptive Card.
- [ ] Notifications are only sent for findings at or above the configured severity threshold.
- [ ] Notification failures are logged but do not block the scan pipeline.

### Estimated Effort: 3–4 hours

---

## 6. Repository Pattern Refactor

### Problem
Database queries are scattered across route handlers and service files. This makes testing difficult (need to mock the entire DB session), creates code duplication, and violates separation of concerns.

### Proposed Solution
- Create `backend/app/db/repositories/` directory with:
  - `scan_repo.py` — `create_scan()`, `get_scan_by_id()`, `list_scans()`, `get_scans_by_repo()`, `get_scan_notifications()`
  - `finding_repo.py` — `bulk_create_findings()`, `get_findings_by_scan()`, `get_findings_by_severity()`
  - `report_repo.py` — `create_report()`, `get_report_by_id()`, `list_reports()`, `update_report_status()`
  - `user_repo.py` — `create_user()`, `get_user_by_username()`, `get_user_repos()`
- Each repository class takes an `AsyncSession` as a constructor argument.
- Refactor route handlers to use repository methods instead of inline queries.
- Add FastAPI dependency injection: `get_scan_repo()` → injects `ScanRepository(session)`.

### Acceptance Criteria
- [ ] Zero inline SQLAlchemy queries remain in route handlers.
- [ ] All existing API tests pass without modification.
- [ ] Repository methods are individually unit-testable with a mock session.

### Estimated Effort: 6–8 hours

---

## 7. Finding Suppression & Allow-Listing

### Problem
Developers cannot suppress known false positives. If a test file legitimately contains a fake API key for testing, it gets flagged on every commit, creating alert fatigue and encouraging developers to ignore findings.

### Proposed Solution
- **Inline suppression:** Support `# icrrg:ignore` or `// icrrg:ignore` comments on the same line or the line above a finding. The detection engines check for this marker before creating a finding.
- **File-level suppression:** In `.icrrg.yml`, allow:
  ```yaml
  suppress:
    files:
      - "tests/fixtures/**"
      - "docs/examples/**"
    rules:
      - rule: "aws-access-key"
        paths: ["tests/**"]
      - rule: "high-entropy-string"
        patterns: ["EXAMPLE_*", "TEST_*"]
  ```
- **Global allow-list:** A new DB table `suppression_rules` managed via an API endpoint (`POST /api/v1/suppressions`) for org-wide suppressions.
- Suppressed findings are still recorded in the database with `suppressed=true` and `suppression_reason` fields for audit purposes.

### Acceptance Criteria
- [ ] Inline `# icrrg:ignore` prevents the finding from being created.
- [ ] `.icrrg.yml` file-level suppression works for glob patterns.
- [ ] Suppressed findings appear in the dashboard under a "Suppressed" tab with the reason.
- [ ] Suppression count is tracked in stats (so teams can monitor suppression abuse).

### Estimated Effort: 6–8 hours

---

## 8. API Rate Limiting

### Problem
No rate limiting exists on any API endpoint. An authenticated user (or compromised token) could flood the scan endpoint, consuming LLM API credits, database storage, and Celery worker capacity.

### Proposed Solution
- Integrate `slowapi` (a FastAPI-compatible rate limiter backed by Redis).
- Define rate limits per endpoint group:
  | Endpoint Group | Limit |
  |---------------|-------|
  | `POST /scans` | 30 requests/minute per user |
  | `POST /reports` | 10 requests/minute per user |
  | `POST /auth/login` | 5 requests/minute per IP |
  | `GET /*` | 120 requests/minute per user |
- Return `429 Too Many Requests` with `Retry-After` header when limits are exceeded.
- Add an admin override: users with `role=admin` get 10x limits.
- Store rate limit counters in Redis (already available as the Celery broker).

### Acceptance Criteria
- [ ] Scan submissions are throttled at 30/min per user.
- [ ] Login attempts are throttled at 5/min per IP (brute-force protection).
- [ ] Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) are included in all responses.
- [ ] Exceeding the limit returns a clear 429 error with retry guidance.

### Estimated Effort: 2–3 hours

### Dependencies
- `pip install slowapi`
- Requires Redis (already in the stack).

---

## 9. JWT Token Refresh & Expiry

### Problem
JWT tokens may have long or no expiry, and there is no refresh mechanism. If a token is compromised, it remains valid indefinitely. This is a significant security risk, especially for a tool handling sensitive security findings.

### Proposed Solution
- Set access token expiry to **15 minutes**.
- Introduce a **refresh token** (stored in an HTTP-only cookie or as a separate JWT with 7-day expiry).
- Add endpoints:
  - `POST /api/v1/auth/refresh` — accepts a valid refresh token, returns a new access token.
  - `POST /api/v1/auth/logout` — invalidates the refresh token (add to a Redis blacklist).
- Store refresh token hashes in a new `refresh_tokens` DB table with columns: `user_id`, `token_hash`, `expires_at`, `revoked`.
- Update the Angular `AuthInterceptor` to automatically call `/refresh` when a 401 is received and retry the original request.
- Add a token rotation policy: each refresh also issues a new refresh token and invalidates the old one (prevents replay attacks).

### Acceptance Criteria
- [ ] Access tokens expire after 15 minutes.
- [ ] Frontend transparently refreshes tokens without user intervention.
- [ ] Logging out invalidates the refresh token server-side.
- [ ] Expired refresh tokens return 401 and redirect to login.

### Estimated Effort: 4–6 hours

---

## Summary & Prioritization Matrix

| # | Feature | Effort | Impact | Risk Reduction | Priority |
|---|---------|--------|--------|----------------|----------|
| 8 | API Rate Limiting | 2–3 hrs | Medium | High | **P1** |
| 9 | JWT Token Refresh | 4–6 hrs | Medium | High | **P1** |
| 5 | Slack/Teams Notifications | 3–4 hrs | High | Low | **P2** |
| 1 | WebSocket Frontend | 3–4 hrs | High | Low | **P2** |
| 7 | Finding Suppression | 6–8 hrs | High | Medium | **P2** |
| 2 | PDF Report Export | 4–6 hrs | High | Low | **P3** |
| 6 | Repository Pattern | 6–8 hrs | Medium | Low | **P3** |
| 3 | Context-Aware Classifier | 8–12 hrs | Very High | High | **P3** |
| 4 | Dependency Scanning | 10–14 hrs | Very High | Very High | **P3** |

**Total estimated effort: 45–65 hours (~2 sprints at 1 developer)**

---

*Document generated for ICRRG project — April 2026*
