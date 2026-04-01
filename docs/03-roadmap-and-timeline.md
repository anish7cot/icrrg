# 03 — Project Roadmap & Timeline

## Hackathon Reality Check

Let me be blunt: hackathons reward **working demos with a compelling narrative**, not feature completeness. I've seen too many teams try to build everything, demo nothing, and walk away with no prize and a Git history full of half-finished branches.

The roadmap below is designed around a **48-hour hackathon window** (standard format), but the phasing also works for a 24-hour or week-long event — you just compress or expand accordingly. Each phase produces a demoable increment. If you run out of time at any phase boundary, you still have something to show.

---

## Phase 0: Foundation (Hours 0–4)

**Goal:** Everyone can run the project locally. All plumbing is in place. No features yet — just working infrastructure.

| Task | Owner Profile | Duration |
|---|---|---|
| Initialize Python project with Poetry, configure `pyproject.toml` | Backend Lead | 30 min |
| Set up FastAPI application skeleton with health check endpoint | Backend Lead | 30 min |
| Install and configure PostgreSQL + Redis locally (or use existing installations) | DevOps / Backend | 45 min |
| Create a startup script (`scripts/start_all.ps1` / `start_all.sh`) that launches all services | DevOps / Backend | 30 min |
| Initialize Angular project with Angular CLI, configure proxy to backend | Frontend Lead | 30 min |
| Set up Angular Material, create shell layout (sidebar, header, content area) | Frontend Lead | 45 min |
| Create database schema (initial migration with Alembic) | Backend | 30 min |
| Set up `.env` files, gitignore, and environment configuration | Everyone | 15 min |
| Confirm end-to-end: Angular → FastAPI → PostgreSQL → response renders | Everyone | 15 min |

**Exit Criteria:** The startup script launches all services. Angular shows a landing page. FastAPI `/health` returns 200. Database accepts connections.

**Demoable:** Not yet — this is scaffolding. But the team is unblocked.

---

## Phase 1: PHI & Secret Detection — The Core Value (Hours 4–14)

**Goal:** A developer can submit a code diff and get back a list of detected PHI/secret leaks with confidence scores.

| Task | Owner Profile | Duration |
|---|---|---|
| Build diff parsing service (accept raw diff text, extract file-level changes) | Backend | 1.5 hr |
| Implement regex rule engine for secret detection (AWS keys, passwords, tokens, connection strings) | ML / Backend | 2 hr |
| Implement entropy analysis for high-randomness string detection | ML / Backend | 1.5 hr |
| Set up spaCy NER pipeline for PHI entity recognition (names, SSN, MRN, DOB patterns) | ML Lead | 2 hr |
| Build the scan API endpoint: `POST /api/v1/scans` — accepts diff, runs pipeline, returns findings | Backend Lead | 1.5 hr |
| Create Angular scan submission view (paste diff or select repo) | Frontend | 1.5 hr |
| Create findings display component (severity badges, line references, entity type) | Frontend | 1.5 hr |
| Test with real-world examples: intentionally plant secrets and PHI in test diffs | Everyone | 1 hr |

**Exit Criteria:** Paste a diff containing a hardcoded AWS key and a patient SSN → system identifies both with appropriate severity and entity type.

**Demoable:** YES. This is your first "wow" moment. Show this working early to build confidence.

---

## Phase 2: Intelligent Code Review (Hours 14–22)

**Goal:** The system can review a commit diff for security vulnerabilities, anti-patterns, and code quality issues using LLM intelligence.

| Task | Owner Profile | Duration |
|---|---|---|
| Design prompt template for code review (system prompt, few-shot examples, output schema) | ML Lead | 2 hr |
| Implement LLM service wrapper (OpenAI API integration with retry, timeout, error handling) | Backend | 1.5 hr |
| Build code review pipeline: diff → context enrichment → prompt construction → LLM call → response parsing | Backend / ML | 2 hr |
| Set up Celery task for async code review (LLM calls are slow — can't block the API) | Backend | 1 hr |
| Integrate code review findings into the results engine (same storage as PHI/secret findings) | Backend | 1 hr |
| Build Angular code review results view (findings grouped by file, severity sorting, expandable explanations) | Frontend | 2 hr |
| Tune prompts based on test results — iterate on false positives and missed findings | ML Lead | 1.5 hr |

**Exit Criteria:** Submit a diff containing a SQL injection vulnerability and an insecure deserialization pattern → system identifies both, explains why they're dangerous, and suggests remediation.

**Demoable:** YES. This is your second "wow" — the AI explains security issues in natural language, specific to your code.

---

## Phase 3: Report Generation (Hours 22–32)

**Goal:** Users can generate role-tailored reports from commit history over a specified time period.

| Task | Owner Profile | Duration |
|---|---|---|
| Build commit history aggregation service (query DB for commits in date range, join with scan results) | Backend | 2 hr |
| Design three prompt templates: Developer, EM, Leadership perspectives | ML Lead | 2 hr |
| Implement report generation pipeline: aggregate data → construct prompt → LLM call → parse response | Backend / ML | 2 hr |
| Build Angular report configuration form (date range, repo selector, audience toggle) | Frontend | 1.5 hr |
| Build Angular report preview component (Markdown rendering with sections, export button) | Frontend | 2 hr |
| Add PDF/Markdown export functionality | Frontend / Backend | 1.5 hr |
| Test with realistic commit histories — ensure reports are coherent and role-appropriate | Everyone | 1 hr |

**Exit Criteria:** Select "Last 2 weeks" + "Engineering Manager" → system generates a delivery-focused report with feature summary, bug metrics, risk areas, and team contributions.

**Demoable:** YES. Show the three different report outputs for the same data — the contrast between developer detail, EM summary, and leadership narrative is visually powerful.

---

## Phase 4: Git Hook Integration & Real Flow (Hours 32–38)

**Goal:** The system works end-to-end with actual git commits, not just pasted diffs. Sensitive data never enters git history.

| Task | Owner Profile | Duration |
|---|---|---|
| Build CLI tool that installs as a git pre-commit hook | Backend / DevOps | 2 hr |
| CLI extracts staged diff (`git diff --cached`), calls scan API, displays results in terminal | Backend | 1.5 hr |
| Implement commit blocking logic (configurable: block on critical, warn on high, info on medium) | Backend | 1 hr |
| Handle edge cases: partial staging (`git add -p`), amend commits, merge commits | Backend | 1 hr |
| Build WebSocket connection for real-time dashboard updates when scans complete | Backend | 1 hr |
| Angular dashboard shows live scan feed with WebSocket updates | Frontend | 1 hr |

**Exit Criteria:** Developer stages a file containing a planted secret, attempts `git commit`, hook fires, scan runs, commit is **blocked before the secret ever enters git history**, and a clear message in the terminal explains why.

**Demoable:** THIS IS YOUR MONEY SHOT. A live demo of a blocked commit — where you then show that `git log` has NO trace of the secret — is the most compelling thing you can show judges. The data never existed in history.

---

## Phase 5: Polish & Demo Prep (Hours 38–46)

**Goal:** Everything looks good, works reliably, and the demo is rehearsed.

| Task | Owner Profile | Duration |
|---|---|---|
| UI polish: loading states, error handling, empty states, responsive layout | Frontend | 2 hr |
| Dashboard landing page with aggregate metrics (total scans, issues found, top issue types) | Frontend | 1.5 hr |
| Trend charts (issues over time, severity distribution) | Frontend | 1.5 hr |
| Seed realistic demo data (don't demo with 2 commits — show a rich history) | Everyone | 1 hr |
| End-to-end testing: run through every demo scenario at least 3 times | Everyone | 1 hr |
| Prepare demo script with talking points and backup plans | Team Lead | 1 hr |

**Exit Criteria:** The demo runs smoothly three times in a row. Every team member can explain every feature. Backup plan exists for API failures.

---

## Phase 6: Buffer & Contingency (Hours 46–48)

**Goal:** Handle the inevitable surprises.

This is your safety net. Things that eat buffer time:
- Service configuration drift between team members' machines
- OpenAI API rate limits or outages
- Database migration conflicts
- "It works on my machine" issues
- Last-minute demo environment setup
- PostgreSQL or Redis installation quirks on Windows

> **Hard Rule:** No new features after Hour 38. Only bug fixes and polish. Feature creep in the last 10 hours has killed more hackathon projects than technical debt ever will.

---

## Feature Priority Matrix (What to Cut If Time Is Short)

| Priority | Feature | Cut Impact |
|---|---|---|
| **P0 — Must Have** | PHI/Secret detection with results display | Without this, don't demo |
| **P0 — Must Have** | Code review with LLM findings | Core differentiator |
| **P1 — Should Have** | Report generation (at least one role) | Significantly weakens pitch |
| **P1 — Should Have** | Git hook integration (live commit block) | Weakens "shift-left" narrative |
| **P2 — Nice to Have** | All three report roles | One role is sufficient for demo |
| **P2 — Nice to Have** | Trend analytics / charts | Dashboard can be simpler |
| **P3 — Stretch** | PDF export | Markdown preview is enough |
| **P3 — Stretch** | Email notifications | Live demo doesn't need this |
| **P3 — Stretch** | WebSocket real-time updates | Polling or manual refresh is fine |

---

## Milestone Summary

```
Hour 0  ─── Phase 0: Foundation ──────────── Infrastructure running
Hour 4  ─── Phase 1: Detection ───────────── PHI/Secret scanning works ✓ [FIRST DEMO POINT]
Hour 14 ─── Phase 2: Code Review ─────────── AI code review works ✓ [SECOND DEMO POINT]
Hour 22 ─── Phase 3: Reports ─────────────── Role-based reports work ✓ [THIRD DEMO POINT]
Hour 32 ─── Phase 4: Git Integration ─────── End-to-end flow works ✓ [MONEY SHOT]
Hour 38 ─── Phase 5: Polish ──────────────── Demo-ready ✓ [FEATURE FREEZE]
Hour 46 ─── Phase 6: Buffer ──────────────── Contingency ✓
Hour 48 ─── DEMO TIME
```

---

## Post-Hackathon Roadmap (If You Win / Want to Continue)

These are the natural extensions that turn a hackathon project into a real product:

1. **Bitbucket App Integration** — Move from git hooks to a proper Bitbucket App that installs on repositories with webhook-driven analysis.
2. **Custom Model Training** — Fine-tune NER models on organization-specific PHI patterns, train a dedicated security classifier on the organization's codebase.
3. **Multi-Language Support** — Extend code review prompts and detection rules beyond the initial language set.
4. **Team Management** — Multi-team, multi-repo support with role-based access control.
5. **Compliance Mapping** — Map findings to HIPAA, SOC2, PCI-DSS requirements for audit evidence.
6. **IDE Plugin** — VS Code extension that runs scans on save, before commit (even further left).
7. **Self-Hosted LLM** — Replace OpenAI dependency with a locally-hosted model for organizations that can't send code to external APIs.
