# 01 — System Requirements

## Overview

This document defines the minimum and recommended system requirements for developing, running, and demoing ICRRG during the hackathon, as well as what a production-grade deployment would look like. We separate these deliberately — a hackathon demo and a production system have very different constraints, and conflating them is a common mistake.

---

## Development Environment (Per Developer Machine)

### Minimum

| Resource | Specification |
|---|---|
| OS | Windows 10/11, macOS 12+, or Ubuntu 20.04+ |
| RAM | 16 GB |
| CPU | 4 cores (Intel i5 10th gen / AMD Ryzen 5 equivalent or better) |
| Disk | 50 GB free SSD space |
| GPU | Not required for hackathon (CPU inference is sufficient for demo) |
| Network | Stable internet for API calls to LLM providers |

### Recommended

| Resource | Specification |
|---|---|
| RAM | 32 GB |
| CPU | 8 cores |
| GPU | NVIDIA GPU with 8 GB+ VRAM (if running local models) |
| Disk | 100 GB NVMe SSD |

---

## Software Prerequisites

### Backend (Python)

| Software | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime for all backend services |
| pip / Poetry | Latest | Dependency management (Poetry preferred for lockfile determinism) |
| Git | 2.40+ | Commit diff extraction, hook integration |
| PostgreSQL | 15+ | Persistent storage for scan results, reports, user data (installed natively) |
| Redis | 7+ | Task queue broker, caching layer (installed natively or via Memurai on Windows) |

### Frontend (Angular)

| Software | Version | Purpose |
|---|---|---|
| Node.js | 20 LTS | Angular build toolchain runtime |
| npm | 10+ | Package management |
| Angular CLI | 17+ | Project scaffolding, build, serve |

### ML / AI Dependencies

| Software | Version | Purpose |
|---|---|---|
| OpenAI API Key | GPT-4 / GPT-4o | Primary LLM for code review and report generation |
| Hugging Face Transformers | 4.36+ | Local model inference (NER for PHI, secret detection) |
| spaCy | 3.7+ | Named Entity Recognition pipeline for PHI patterns |
| scikit-learn | 1.3+ | Custom classifier training for secret detection |

> **Decision Point:** For hackathon, lean on OpenAI API for heavy lifting (code review, report generation) and use lightweight local models (regex + spaCy NER) for PHI/secret detection. This keeps inference fast and avoids GPU dependencies during the demo.

---

## Infrastructure (Hackathon Demo)

For the hackathon, everything runs locally on your machine — no containers, no Kubernetes, no microservices mesh. Each service runs as a native process. A startup script orchestrates them.

| Component | Hackathon Setup |
|---|---|
| Backend API | Single FastAPI process via `uvicorn app.main:app --reload` |
| Frontend | `ng serve` (Angular dev server with proxy to backend) |
| Database | PostgreSQL installed natively (Windows installer / Homebrew / apt) |
| Task Queue | Redis installed natively (Memurai on Windows / Homebrew / apt) + Celery worker process |
| ML Models | CPU inference, loaded in-process or via a single model service |
| Git Integration | Local git hooks + REST API for Bitbucket webhook simulation |

### Single VM Spec (if deploying to cloud for demo)

| Resource | Specification |
|---|---|
| Provider | AWS EC2 / Azure VM / GCP Compute |
| Instance | t3.xlarge equivalent (4 vCPU, 16 GB RAM) |
| Disk | 80 GB gp3 SSD |
| OS | Ubuntu 22.04 LTS |

---

## Infrastructure (Production Vision)

This is what the architecture would look like beyond the hackathon. Include this in your pitch to show you've thought past the demo.

| Component | Production Setup |
|---|---|
| Backend API | Containerized FastAPI behind load balancer (2+ replicas) |
| Frontend | Angular static build on CDN (CloudFront / Azure CDN) |
| Database | Managed PostgreSQL (RDS / Azure Database / Cloud SQL) |
| Task Queue | Managed Redis (ElastiCache / Azure Cache) + Celery workers (autoscaled) |
| ML Models | Dedicated model serving (GPU instances or serverless inference endpoints) |
| Git Integration | Bitbucket App / Bitbucket Webhook subscriptions |
| Auth | OAuth 2.0 / OIDC via identity provider |
| Monitoring | Prometheus + Grafana, structured logging to ELK or Datadog |
| CI/CD | Bitbucket Pipelines / Azure DevOps pipelines |

---

## External Service Dependencies

| Service | Required? | Purpose | Fallback |
|---|---|---|---|
| OpenAI API | Yes (for hackathon) | Code review intelligence, report generation | Azure OpenAI or local Llama/Mistral model |
| Bitbucket API | Yes | Fetch commits, diffs, PR metadata | Direct git CLI extraction as fallback |
| SMTP / Email Service | Optional | Notification delivery for reports | In-app notification only |

---

## Environment Variables (Expected)

The system will require the following environment configuration. This is not exhaustive but covers the critical pieces:

- LLM API keys and endpoint URLs
- Database connection string
- Redis connection string
- Bitbucket OAuth credentials (workspace and repository access)
- Secret encryption key for storing scan results
- Application secret key for session/token signing
- CORS allowed origins for frontend

> **Security Note:** No secrets should ever be committed to the repository. Use `.env` files locally (gitignored) and proper secret management (Vault, AWS Secrets Manager, Azure Key Vault) in production.

---

## Browser Support (Frontend)

| Browser | Version |
|---|---|
| Chrome | Latest 2 versions |
| Firefox | Latest 2 versions |
| Edge | Latest 2 versions |
| Safari | Latest 2 versions |

---

## Summary

The hackathon setup is deliberately lean — one machine, natively installed services, a startup script, and your API keys. No containers, no orchestration layers. The production vision shows judges and stakeholders that the team understands scale. Don't over-engineer the demo; spend the time on making the AI pipeline sharp and the demo compelling.
