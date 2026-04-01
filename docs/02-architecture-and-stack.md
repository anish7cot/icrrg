# 02 — Architecture & Tech Stack

## Design Philosophy

Three principles govern every architectural decision here:

1. **Shift-left, not shift-around.** The value proposition is catching problems at commit time — not after CI, not after merge, not after deploy. Every design choice should optimize for speed at the point of commit.

2. **ML as augmentation, not replacement.** We're not building a system that replaces human reviewers. We're building one that catches what humans consistently miss (secrets, PHI patterns, known vulnerability signatures) and generates the tedious artifacts humans hate writing (release notes).

3. **Demo-first, scale-later.** This is a hackathon. The architecture must be simple enough to stand up in hours, but the design must be credible enough to scale. We achieve this by making the right abstractions now, even if the implementation behind them is simple.

---

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DEVELOPER WORKFLOW                       │
│                                                                 │
│   git commit ──► Pre-commit Hook ──► ICRRG Analysis API        │
│                                          │                      │
│                              ┌───────────┴───────────┐          │
│                              ▼                       ▼          │
│                     PHI/Secret Scanner     Code Review Engine   │
│                     (Local ML Pipeline)    (LLM-Powered)        │
│                              │                       │          │
│                              └───────────┬───────────┘          │
│                                          ▼                      │
│                                   Results Engine                │
│                                   (Score, Classify, Store)      │
│                                          │                      │
│                              ┌───────────┴───────────┐          │
│                              ▼                       ▼          │
│                     Developer Feedback        Dashboard &       │
│                     (CLI / Terminal)          Reports (Angular)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     REPORT GENERATION FLOW                      │
│                                                                 │
│   Commit History ──► Aggregation Engine ──► LLM Summarizer     │
│   (Git Log + DB)     (Filter by date,       (Prompt per role)   │
│                       author, module)              │             │
│                                            ┌───────┴──────┐     │
│                                            ▼       ▼      ▼    │
│                                          Dev     EM    Leader   │
│                                         Report  Report  Report  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Git Integration Layer

**What it does:** Intercepts commits at the pre-commit stage — before code ever enters git history — extracts staged diffs, and sends them to the analysis API.

**Why pre-commit instead of pre-push?**
With a pre-push hook, sensitive data already exists in local git history. Even if the push is blocked, the secret or PHI is baked into a commit object — visible to anyone who clones the repo, and removable only via `git rebase` or `git filter-branch`. With pre-commit, the data is caught while still in the **staging area**. It never enters a commit object. It never exists in git history. This is the true shift-left position.

**How it works:**
- A git pre-commit hook triggers on every `git commit` attempt
- The hook extracts the staged diff (`git diff --cached`) — only the changes about to be committed
- Sends the diff to the backend API for analysis
- Blocks the commit if critical issues are found (configurable severity threshold)
- Also supports webhook-based flow for Bitbucket integration (post-push analysis for teams as a secondary safety net)

**Stack choice:** Git hooks are shell scripts that invoke a lightweight Python CLI client. The CLI is pip-installable and wraps HTTP calls to the backend. For webhook mode, the backend exposes a `/webhooks/bitbucket` endpoint.

---

### 2. PHI & Secret Detection Engine

**What it does:** Scans commit diffs for protected health information (PHI) and hardcoded secrets.

**Architecture:**
- **Layer 1 — Regex Pattern Matching:** Fast, deterministic scan for known patterns (SSN formats, credit card numbers, AWS keys, private keys, connection strings, common password variable names). This is your first line of defense and runs in milliseconds.
- **Layer 2 — NER (Named Entity Recognition):** spaCy-based NER model fine-tuned to recognize healthcare-specific entities (patient names in context, MRN patterns, diagnosis codes appearing in non-configuration contexts).
- **Layer 3 — Entropy Analysis:** High-entropy string detection for catching secrets that don't match known patterns — random-looking strings assigned to variables named `key`, `secret`, `token`, `password`, etc.
- **Layer 4 — Context-Aware Classification:** A lightweight classifier that reduces false positives by analyzing the surrounding code context. Is this a test fixture with dummy data? Is this a configuration template with placeholder values? The model learns to distinguish real leaks from noise.

**Stack:**
- spaCy 3.7+ with custom NER pipeline
- scikit-learn for the context classifier
- Custom regex rule engine (Python `re` module, organized as configurable rule sets)

**Why not just use an existing tool like Gitleaks or TruffleHog?**
Those tools are excellent for regex/entropy scanning but they don't do PHI-specific NER, they don't do context-aware false-positive reduction, and they can't feed into a unified reporting pipeline. We use them as *inspiration* for our regex layer but build our own pipeline to own the full analysis chain.

---

### 3. Code Review Engine

**What it does:** Performs intelligent code review on commit diffs — identifying security vulnerabilities, anti-patterns, and code quality issues.

**Architecture:**
- Receives the diff payload from the Git Integration Layer
- Constructs a structured prompt with the diff, file context (what the file does, its imports, its module), and analysis instructions
- Sends to the LLM (OpenAI GPT-4) with a system prompt that acts as a senior security-focused code reviewer
- Parses the structured response (JSON schema enforced via function calling / structured outputs)
- Classifies findings by severity: Critical, High, Medium, Low, Info
- Maps findings to industry frameworks where applicable (OWASP Top 10, CWE IDs)

**Stack:**
- OpenAI API (GPT-4 / GPT-4o) via the `openai` Python SDK
- Prompt engineering with few-shot examples for consistent output structure
- Pydantic models for response validation and parsing

**Why LLM instead of traditional SAST?**
Traditional SAST tools (SonarQube, Semgrep) are rule-based — they catch known patterns but miss novel anti-patterns and can't explain *why* something is a problem in natural language. The LLM augments (not replaces) SAST by providing contextual, explainable reviews. For hackathon scope, LLM alone is sufficient. In production, you'd layer both.

---

### 4. Results Engine

**What it does:** Aggregates, scores, classifies, and persists all analysis results.

**Architecture:**
- Receives findings from both the PHI/Secret Engine and the Code Review Engine
- Assigns a composite risk score to the commit
- Stores results in PostgreSQL with full audit trail
- Triggers notifications based on severity thresholds
- Provides the data layer for the dashboard and report generation

**Stack:**
- PostgreSQL 15+ for persistence
- SQLAlchemy 2.0 as ORM (async support)
- Redis for caching frequently accessed data (recent scans, dashboard metrics)

---

### 5. Report Generation Engine

**What it does:** Generates natural-language reports from commit history, tailored to the reader's role.

**Architecture:**
- User selects a date range, repository, and target audience (Developer / Engineering Manager / Leadership)
- The engine queries commit history and associated scan results from the database
- Aggregates data by module, author, severity, type
- Constructs a role-specific prompt:
  - **Developer report:** Technical changelog — what changed, what broke, what was fixed, what needs attention
  - **EM report:** Delivery summary — features completed, bugs fixed, velocity trends, risk areas, team contribution distribution
  - **Leadership report:** Business narrative — release readiness, risk posture, compliance status, high-level feature summary in business language
- Sends to LLM for natural language generation
- Returns structured report with sections, optionally exportable to PDF/Markdown

**Stack:**
- OpenAI API for report generation
- Jinja2 templates for report structure scaffolding before LLM enhancement
- WeasyPrint or reportlab for PDF export (stretch goal)

---

### 6. Angular Dashboard (Frontend)

**What it does:** Provides the visual interface for the entire platform.

**Key Views:**
- **Scan Dashboard:** Real-time feed of recent commit scans, filterable by repo/author/severity
- **Commit Detail View:** Deep dive into a specific commit's findings with inline diff annotations
- **Report Generator:** Form to configure and generate role-based reports, with preview and export
- **Trend Analytics:** Charts showing issue trends over time, most common vulnerability types, top contributors to debt
- **Settings:** API key configuration, severity thresholds, notification preferences

**Stack:**
- Angular 17+ with standalone components
- Angular Material for UI component library
- NgRx or Angular Signals for state management (prefer Signals for hackathon simplicity)
- Chart.js or ngx-charts for data visualization
- RxJS for reactive data flows and real-time updates

---

### 7. API Layer (Backend)

**What it does:** Central nervous system — all requests flow through here.

**Architecture:**
- RESTful API with clear resource-oriented endpoints
- Async request handling for ML inference operations
- Background task processing via Celery for long-running analysis
- WebSocket support for real-time scan status updates to the dashboard

**Stack:**
- FastAPI (async, auto-docs via OpenAPI/Swagger, Pydantic validation)
- Celery + Redis for async task queue
- Uvicorn as ASGI server
- Alembic for database migrations

**Why FastAPI over Django/Flask?**
- Native async support matters when you're making multiple LLM API calls per request
- Automatic OpenAPI documentation is a hackathon advantage (live API docs for judges)
- Pydantic integration means request/response validation is essentially free
- FastAPI's performance characteristics are better suited for an API-heavy workload

---

## Tech Stack Summary

| Layer | Technology | Justification |
|---|---|---|
| **Backend Framework** | FastAPI | Async-native, auto-docs, Pydantic integration |
| **Language (Backend)** | Python 3.11+ | ML ecosystem, LLM SDK availability, team preference |
| **Frontend Framework** | Angular 17+ | Enterprise-grade, TypeScript-first, strong component model |
| **UI Components** | Angular Material | Rapid UI development, consistent design language |
| **Database** | PostgreSQL 15 | Reliable, rich JSON support for storing flexible scan results |
| **Cache / Queue Broker** | Redis 7 | Fast, dual-purpose as both cache and Celery broker |
| **Task Queue** | Celery | Battle-tested async task processing for Python |
| **ORM** | SQLAlchemy 2.0 (async) | Mature, flexible, excellent migration support via Alembic |
| **PHI/NER Detection** | spaCy 3.7 | Production-grade NER, fast inference, customizable pipelines |
| **Secret Detection** | Custom (regex + entropy + sklearn) | Tailored rules, low false-positive design |
| **Code Review AI** | OpenAI GPT-4 / GPT-4o | Best-in-class reasoning for code understanding |
| **Report Generation** | OpenAI GPT-4 + Jinja2 | Natural language fluency + structural templating |
| **Containerization** | None (native local processes) | No Docker constraint — uses startup script for service orchestration |
| **API Documentation** | Swagger/OpenAPI (auto-generated) | Free from FastAPI, impressive for demo |

---

## Data Flow Summary

```
Developer stages changes and runs `git commit`
        │
        ▼
Git pre-commit hook fires
        │
        ▼
CLI extracts staged diff (`git diff --cached`), sends to POST /api/v1/scans
        │
        ├──► PHI/Secret Detection (sync, fast — regex + NER)
        │           │
        │           ▼
        │    Findings with confidence scores
        │
        ├──► Code Review (async via Celery — LLM call)
        │           │
        │           ▼
        │    Structured review with severity classification
        │
        ▼
Results Engine aggregates findings
        │
        ├──► Store in PostgreSQL
        ├──► Return summary to CLI (block/allow commit decision)
        ├──► Push to WebSocket (real-time dashboard update)
        └──► Trigger notification if critical findings
```

---

## Integration Points

| Integration | Protocol | Direction |
|---|---|---|
| Git (local) | Pre-commit hook → HTTP | Outbound from dev machine to API |
| Bitbucket | Webhooks → HTTP | Inbound to API from Bitbucket |
| OpenAI | HTTPS REST | Outbound from API to OpenAI |
| Frontend | HTTP REST + WebSocket | Bidirectional between Angular and FastAPI |
| Email / Notifications | SMTP / Webhook | Outbound from API (stretch goal) |

---

## Security Considerations (Built Into Architecture)

- All LLM API calls go through the backend — the frontend never directly calls OpenAI. This prevents API key exposure.
- Commit diffs are processed in memory and only findings (not raw source code) are persisted long-term.
- PHI detection results are encrypted at rest in the database — you're storing information *about* PHI detection, which itself needs protection.
- All API endpoints require authentication (JWT-based for hackathon, OAuth 2.0 for production).
- Rate limiting on the scan endpoint to prevent abuse.
- Input validation on all endpoints via Pydantic schemas — no raw string processing.

---

## What We Intentionally Do NOT Build (Scope Boundaries)

- We do not build a full CI/CD pipeline integration (that's a post-hackathon extension)
- We do not build custom ML model training infrastructure (we use pre-trained models and prompt engineering)
- We do not build a multi-tenant SaaS platform (single-tenant for hackathon)
- We do not build mobile apps
- We do not replace existing SAST/DAST tools — we augment them
