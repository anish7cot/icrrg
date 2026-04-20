# 05 — Folder Structure Guide

## Design Rationale

This structure is opinionated. It separates the backend, frontend, and shared configuration into distinct top-level directories. Within the backend, modules are organized by **domain concern** (detection, review, reports), not by technical layer (models, services, controllers). This means when you're working on PHI detection, everything you need is in one place — not scattered across five directories.

The frontend follows Angular's module-per-feature convention with standalone components (Angular 17+ style).

---

## Full Project Structure

```
Hackathon/
│
├── README.md                                   # Project overview and documentation index
├── docs/                                       # All project documentation
│   ├── 01-system-requirements.md
│   ├── 02-architecture-and-stack.md
│   ├── 03-roadmap-and-timeline.md
│   ├── 04-bottlenecks-and-challenges.md
│   ├── 05-folder-structure-guide.md
│   └── 06-team-roles.md
│
├── .env.example                                # Template for environment variables
├── .gitignore                                  # Git ignore rules
│
├── backend/                                    # Python backend (FastAPI)
│   ├── pyproject.toml                          # Poetry project definition
│   ├── poetry.lock                             # Locked dependencies
│   ├── alembic.ini                             # Alembic migration configuration
│   ├── alembic/                                # Database migrations
│   │   ├── env.py
│   │   └── versions/                           # Migration scripts (auto-generated)
│   │
│   ├── app/                                    # Application source code
│   │   ├── main.py                             # FastAPI application entry point
│   │   ├── config.py                           # Settings management (Pydantic BaseSettings)
│   │   ├── dependencies.py                     # FastAPI dependency injection setup
│   │   │
│   │   ├── api/                                # API layer — route definitions only
│   │   │   ├── v1/                             # API version 1
│   │   │   │   ├── router.py                   # Aggregates all v1 routers
│   │   │   │   ├── auth.py                     # POST /auth/register, /auth/login, GET /auth/me
│   │   │   │   ├── scans.py                    # POST /scans, GET /scans/{id}, GET /scans
│   │   │   │   ├── reports.py                  # POST /reports, GET /reports/{id}
│   │   │   │   ├── stats.py                    # GET /stats (dashboard metrics), GET /stats/trends
│   │   │   │   ├── eval.py                     # POST /eval/run, GET /eval/runs, GET /eval/runs/{id}
│   │   │   │   ├── feedback.py                 # POST /findings/{id}/feedback, GET /findings/accuracy, GET /findings/scan/{id}/accuracy
│   │   │   │   ├── commits.py                  # GET /commits (history retrieval)
│   │   │   │   ├── dashboard.py                # GET /dashboard/metrics
│   │   │   │   └── webhooks.py                 # POST /webhooks/bitbucket
│   │   │
│   │   ├── detection/                          # PHI & Secret Detection domain
│   │   │   ├── service.py                      # Orchestrates the detection pipeline
│   │   │   ├── regex_engine.py                 # Pattern-based secret detection rules
│   │   │   ├── entropy.py                      # Entropy analysis for randomness detection
│   │   │   ├── ner_pipeline.py                 # spaCy NER for PHI entity recognition
│   │   │   ├── context_classifier.py           # False-positive reduction classifier
│   │   │   ├── rules/                          # Detection rule definitions
│   │   │   │   ├── secrets.py                  # AWS, GCP, Azure, generic patterns
│   │   │   │   ├── phi.py                      # SSN, MRN, DOB, phone patterns
│   │   │   │   └── custom.py                   # Team-specific custom rules
│   │   │   └── schemas.py                      # Pydantic models for detection results
│   │   │
│   │   ├── review/                             # Code Review domain (LLM-powered)
│   │   │   ├── service.py                      # Orchestrates the review pipeline
│   │   │   ├── prompt_builder.py               # Constructs prompts from diff + context
│   │   │   ├── prompts/                        # Prompt templates
│   │   │   │   ├── system.py                   # System prompt for code review persona
│   │   │   │   └── few_shot.py                 # Few-shot examples for output consistency
│   │   │   ├── response_parser.py              # Parses and validates LLM responses
│   │   │   └── schemas.py                      # Pydantic models for review results
│   │   │
│   │   ├── reports/                            # Report Generation domain
│   │   │   ├── service.py                      # Orchestrates report generation
│   │   │   ├── aggregator.py                   # Queries and aggregates commit/scan data
│   │   │   ├── prompt_builder.py               # Role-specific prompt construction
│   │   │   ├── templates/                      # Jinja2 templates for report scaffolding
│   │   │   │   ├── developer.j2
│   │   │   │   ├── manager.j2
│   │   │   │   └── leadership.j2
│   │   │   ├── exporter.py                     # PDF/Markdown export functionality
│   │   │   └── schemas.py                      # Pydantic models for reports
│   │   │
│   │   ├── git/                                # Git Integration domain
│   │   │   ├── diff_parser.py                  # Parses raw diff text into structured data
│   │   │   ├── commit_service.py               # Fetches commit history and metadata
│   │   │   └── webhook_handler.py              # Processes incoming Bitbucket webhooks
│   │   │
│   │   ├── llm/                                # LLM abstraction layer
│   │   │   ├── base.py                         # Abstract LLM interface
│   │   │   ├── openai_provider.py              # OpenAI API implementation
│   │   │   ├── mock_provider.py                # Mock responses for testing/demo backup
│   │   │   └── schemas.py                      # Shared LLM request/response models
│   │   │
│   │   ├── db/                                 # Database layer
│   │   │   ├── session.py                      # SQLAlchemy async session setup
│   │   │   ├── models/                         # SQLAlchemy ORM models
│   │   │   │   ├── scan.py                     # Scan and ScanFinding models
│   │   │   │   ├── commit.py                   # Commit metadata model
│   │   │   │   ├── report.py                   # Generated report model
│   │   │   │   └── base.py                     # Base model with common fields
│   │   │   └── repositories/                   # Data access layer (query logic)
│   │   │       ├── scan_repo.py
│   │   │       ├── commit_repo.py
│   │   │       └── report_repo.py
│   │   │
│   │   ├── tasks/                              # Celery async tasks
│   │   │   ├── celery_app.py                   # Celery configuration
│   │   │   ├── review_task.py                  # Async code review task
│   │   │   └── report_task.py                  # Async report generation task
│   │   │
│   │   └── core/                               # Cross-cutting concerns
│   │       ├── security.py                     # Auth, JWT, API key validation
│   │       ├── exceptions.py                   # Custom exception classes
│   │       └── scoring.py                      # Risk scoring logic
│   │
│   ├── cli/                                    # CLI tool for git hook integration
│   │   ├── main.py                             # CLI entry point (click or typer)
│   │   ├── hook_installer.py                   # Installs/uninstalls git pre-commit hook
│   │   └── scanner.py                          # Extracts diff and calls API
│   │
│   └── tests/                                  # Backend tests
│       ├── conftest.py                         # Shared fixtures
│       ├── test_detection/                     # Detection engine tests
│       │   ├── test_regex_engine.py
│       │   ├── test_entropy.py
│       │   └── test_ner_pipeline.py
│       ├── test_review/                        # Code review tests
│       │   └── test_prompt_builder.py
│       ├── test_reports/                       # Report generation tests
│       │   └── test_aggregator.py
│       ├── test_api/                           # API endpoint tests
│       │   └── test_scans.py
│       └── fixtures/                           # Test data
│           ├── sample_diffs/                   # Sample diff files for testing
│           └── sample_responses/               # Mock LLM responses
│
├── frontend/                                   # Angular frontend
│   ├── angular.json                            # Angular workspace configuration
│   ├── package.json                            # npm dependencies
│   ├── tsconfig.json                           # TypeScript configuration
│   │
│   └── src/
│       ├── main.ts                             # Application bootstrap
│       ├── index.html                          # Root HTML
│       ├── styles.scss                         # Global styles (Angular Material theme)
│       │
│       ├── app/
│       │   ├── app.component.ts                # Root app component
│       │   ├── app.routes.ts                   # Route definitions
│       │   ├── app.config.ts                   # Application configuration
│       │   │
│       │   ├── core/                           # Singleton services and guards
│       │   │   ├── services/
│       │   │   │   ├── api.service.ts          # HTTP client wrapper
│       │   │   │   ├── scan.service.ts         # Scan-related API calls
│       │   │   │   ├── report.service.ts       # Report-related API calls
│       │   │   │   ├── dashboard.service.ts    # Dashboard metrics API calls
│       │   │   │   └── websocket.service.ts    # WebSocket connection management
│       │   │   ├── guards/
│       │   │   │   └── auth.guard.ts           # Route protection
│       │   │   └── interceptors/
│       │   │       └── auth.interceptor.ts     # JWT token injection
│       │   │
│       │   ├── shared/                         # Reusable components and utilities
│       │   │   ├── components/
│       │   │   │   ├── severity-badge/         # Color-coded severity indicator
│       │   │   │   ├── finding-card/           # Individual finding display
│       │   │   │   ├── diff-viewer/            # Inline diff display with annotations
│       │   │   │   └── loading-spinner/        # Loading state component
│       │   │   ├── pipes/
│       │   │   │   └── time-ago.pipe.ts        # Relative time display
│       │   │   └── models/
│       │   │       ├── scan.model.ts           # TypeScript interfaces for scan data
│       │   │       ├── report.model.ts         # TypeScript interfaces for reports
│       │   │       └── finding.model.ts        # TypeScript interfaces for findings
│       │   │
│       │   └── features/                       # Feature modules (each is a page/view)
│       │       ├── dashboard/                  # Main dashboard view
│       │       │   ├── dashboard.component.ts
│       │       │   ├── dashboard.component.html
│       │       │   ├── dashboard.component.scss
│       │       │   └── widgets/               # Dashboard chart/metric components
│       │       │       ├── scan-feed/
│       │       │       ├── severity-chart/
│       │       │       └── metrics-summary/
│       │       │
│       │       ├── scan/                       # Scan submission and results
│       │       │   ├── scan-submit/            # Form to submit diff for scanning
│       │       │   │   ├── scan-submit.component.ts
│       │       │   │   ├── scan-submit.component.html
│       │       │   │   └── scan-submit.component.scss
│       │       └── scan-detail/            # Detailed view of scan results + accuracy panel
│       │       │       ├── scan-detail.component.ts   # Loads findings, accuracy, handles feedback
│       │       │       ├── scan-detail.component.html  # Accuracy panel, per-finding verdict buttons
│       │       │       └── scan-detail.component.scss  # Severity colors, accuracy panel styles
│       │       │
│       │       ├── reports/                    # Report generation and viewing
│       │       │   ├── report-config/          # Report configuration form
│       │       │   ├── report-preview/         # Report preview with export
│       │       │   └── report-history/         # Past generated reports
│       │       │
│       │       └── settings/                   # Application settings
│       │           └── settings.component.ts
│       │
│       ├── assets/                             # Static assets
│       │   ├── icons/
│       │   └── images/
│       │
│       └── environments/                       # Environment configuration
│           ├── environment.ts
│           └── environment.prod.ts
│
└── scripts/                                    # Utility scripts
    ├── seed_demo_data.py                       # Populates DB with realistic demo data
    ├── start_all.ps1                           # Windows: starts all services (PostgreSQL, Redis, backend, Celery, frontend)
    ├── start_all.sh                            # Mac/Linux: starts all services
    ├── setup_dev.sh                            # One-command dev environment setup
    └── install_hooks.sh                        # Installs git hooks in target repo
```

---

## Directory Responsibilities

### Backend: Domain-Driven Organization

| Directory | Responsibility | Changes Frequently? |
|---|---|---|
| `app/api/v1/` | HTTP route definitions only — thin controllers that call services. Includes auth, scans, reports, stats, eval, and feedback endpoints. | Rarely after initial setup |
| `app/detection/` | Everything related to PHI and secret scanning | Heavily during Phase 1 |
| `app/review/` | Everything related to LLM code review | Heavily during Phase 2 |
| `app/reports/` | Everything related to report generation | Heavily during Phase 3 |
| `app/git/` | Git diff parsing and commit history retrieval | Phase 1 and 4 |
| `app/llm/` | LLM provider abstraction — shared by review and reports | Stable after Phase 2 |
| `app/db/` | Database models, sessions, and query logic | Stable after Phase 0 |
| `app/tasks/` | Celery async task definitions | Phase 2 onward |
| `app/core/` | Cross-cutting: auth, exceptions, scoring | Evolves throughout |
| `cli/` | Developer-facing CLI for git hook integration | Phase 4 |

### Frontend: Feature-Module Organization

| Directory | Responsibility | Changes Frequently? |
|---|---|---|
| `core/services/` | API communication, singleton services | Grows with each feature |
| `shared/components/` | Reusable UI atoms (badges, cards, viewers) | Grows then stabilizes |
| `shared/models/` | TypeScript interfaces mirroring backend schemas | Mirrors backend changes |
| `features/dashboard/` | Main landing page with metrics and scan feed | Phase 5 polish |
| `features/scan/` | Scan submission form and results detail view | Phase 1–2 |
| `features/reports/` | Report configuration, preview, and history | Phase 3 |
| `features/settings/` | App configuration UI | Stretch goal |

---

## Key Conventions

### File Naming
- **Backend:** Snake case everywhere. `regex_engine.py`, `scan_repo.py`, `prompt_builder.py`.
- **Frontend:** Kebab case with Angular suffix convention. `scan-detail.component.ts`, `severity-badge.component.ts`, `scan.service.ts`.

### Import Organization
- **Backend:** Order — stdlib, third-party, local. Use absolute imports from `app.*`. 
- **Frontend:** Order — Angular imports, third-party, local. Use path aliases if `tsconfig.json` defines them.

### Schema/Model Parity
- Every backend Pydantic response model should have a corresponding TypeScript interface in `shared/models/`. Keep these in sync manually during the hackathon. In production, you'd auto-generate the TypeScript from the OpenAPI spec.

### Test Co-location
- Backend tests mirror the `app/` structure under `tests/`. Test file names mirror source file names with `test_` prefix.
- Frontend tests use Angular's default co-located `.spec.ts` files next to their components.

---

## What NOT to Create

- **No `utils/` junk drawer.** If a utility belongs to a domain, put it in that domain's directory. If it's truly generic (e.g., retry logic), it goes in `core/`.
- **No `helpers/` directory.** Same reason. Name things by what they do, not by their informal designation.
- **No `common/` directory.** Use `core/` for cross-cutting concerns and `shared/` for reusable frontend components.
- **No nested `src/` inside `backend/`.** The `app/` directory IS the source root for the backend. Don't add another layer.
