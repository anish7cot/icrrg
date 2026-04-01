# 06 — Team Roles & Responsibilities

## How to Use This Document

This isn't an org chart — it's a workload distribution plan. In a hackathon, everyone touches everything. But without clear ownership, you get two people building the same thing and nobody building the hard thing. Each role below is a **primary responsibility**, not an exclusive boundary. Cross-pollinate freely, but know whose name is on each deliverable.

This document scales for teams of 2 to 5. Adjust by merging roles for smaller teams.

---

## Role Definitions

### 1. Backend Lead / API Architect

**Primary Ownership:** FastAPI application, API contracts, database layer, Celery task infrastructure.

**What success looks like for this role:**
- The API is running and documented (Swagger UI) by end of Phase 0
- Every frontend developer can work against stable endpoints without waiting for backend changes
- Database migrations run cleanly, and the schema supports all three domains (scans, reviews, reports)
- Celery workers process async tasks reliably

**Key decisions this person makes:**
- API endpoint naming and versioning conventions
- Database schema design and when to migrate
- How background tasks are structured and monitored
- Error handling strategy (what returns 400, 422, 500 and when)

**Interfaces with:** ML/AI Lead (integrating detection and review pipelines into API), Frontend Lead (API contracts)

---

### 2. ML / AI Lead

**Primary Ownership:** PHI detection pipeline, secret detection rules, LLM prompt engineering, report generation logic.

**What success looks like for this role:**
- The regex engine catches at least 90% of common secret patterns without drowning in false positives
- The spaCy NER pipeline recognizes healthcare-specific entities in code context
- LLM prompts produce structured, consistent, useful code reviews
- Report generation produces meaningfully different outputs for each role
- The team has high confidence in the demo scenarios — they've been tested and tuned

**Key decisions this person makes:**
- Detection rule definitions (what patterns to scan for)
- NER model selection and training data approach
- LLM prompt design, temperature settings, and output schema
- The threshold between blocking findings and informational findings
- When to use LLM vs when local models are sufficient

**Interfaces with:** Backend Lead (pipeline integration into API), everyone (demo scenario design)

---

### 3. Frontend Lead

**Primary Ownership:** Angular application, all UI views, data visualization, user experience.

**What success looks like for this role:**
- The dashboard loads and looks professional within 5 seconds of opening the app
- Scan results are easy to read — severity is visually obvious, findings are expandable, diffs are highlighted
- Report generation flow is intuitive — configure, preview, export
- Loading states, error states, and empty states are all handled (nothing looks broken during demo)
- Charts and metrics make the data feel impactful

**Key decisions this person makes:**
- UI component library usage and customization
- Data visualization library and chart types
- State management approach (Signals vs NgRx vs plain services)
- How real-time updates are displayed
- Color scheme, typography, and visual hierarchy

**Interfaces with:** Backend Lead (API consumption, WebSocket integration), Team Lead (demo flow design)

---

### 4. DevOps / Infrastructure Owner

**Primary Ownership:** Local service orchestration scripts, CI environment, demo machine preparation, git hook tooling.

**What success looks like for this role:**
- The startup script (`start_all.ps1` / `start_all.sh`) launches the entire stack from zero reliably
- PostgreSQL and Redis are installed and configured on all team members’ machines
- The demo machine is set up, tested, and has all dependencies pre-installed
- Git hooks install and execute reliably on the demo machine
- Environment variables are documented and the `.env.example` is complete
- If deploying to cloud for demo, the VM is provisioned and configured

**Key decisions this person makes:**
- Service startup order and health check verification in scripts
- Port assignments and ensuring no conflicts across services
- How environment configuration flows from `.env` to each service
- Demo machine selection and preparation timeline
- OS-specific installation guidance (Windows PostgreSQL installer, Memurai for Redis, etc.)

**Interfaces with:** Backend Lead (backend service configuration), Frontend Lead (frontend proxy setup), Team Lead (demo logistics)

> **Note for small teams:** This role is often merged with Backend Lead. That's fine — but the startup scripts and demo machine prep still need to happen. Don't let it fall through the cracks.

---

### 5. Team Lead / Demo Owner

**Primary Ownership:** Scope management, demo script, presentation, stakeholder narrative.

**What success looks like for this role:**
- The team ships a working demo — not a collection of features that don't quite connect
- The demo tells a story: problem → solution → live proof → impact → future vision
- No feature was built that doesn't appear in the demo
- The presentation fits within the time limit and every second earns its place
- Backup plans exist for every point of failure in the demo

**Key decisions this person makes:**
- What features get built and what gets cut (scope authority)
- Demo flow and talking points
- Who presents which section
- When to stop building and start polishing (enforces feature freeze)
- Risk mitigation and backup plan activation

**Interfaces with:** Everyone (scope negotiation, demo rehearsal, progress check-ins)

> **Note:** This role can be combined with any technical role, but the scope management and demo ownership duties are non-negotiable. Someone has to own the "are we building the right thing?" question.

---

## Team Size Configurations

### 2-Person Team

| Person | Roles Combined |
|---|---|
| Person A | Backend Lead + ML/AI Lead + DevOps |
| Person B | Frontend Lead + Team Lead |

**The hard truth:** With two people, you'll need to scope aggressively. Cut the git hook integration (Phase 4) and the trends/charts (Phase 5). Focus on a clean scan submission flow and one role's report generation. Your demo will be simpler, but it can still win if the AI output is impressive and the narrative is strong.

---

### 3-Person Team (Sweet Spot for Hackathon)

| Person | Roles Combined |
|---|---|
| Person A | Backend Lead + DevOps |
| Person B | ML/AI Lead |
| Person C | Frontend Lead + Team Lead |

**This is the ideal hackathon team size.** Three people means low coordination overhead, clear ownership, and enough hands to build the full P0+P1 feature set. Person B is the critical path — the ML/AI work determines whether the demo is "cool tool" or "that's just a form."

---

### 4-Person Team

| Person | Roles Combined |
|---|---|
| Person A | Backend Lead |
| Person B | ML/AI Lead |
| Person C | Frontend Lead |
| Person D | DevOps + Team Lead |

**The fourth person as DevOps + Team Lead is powerful.** They handle all the infrastructure friction that slows down the other three, and they own the demo narrative. This configuration lets the three technical leads focus purely on feature delivery.

---

### 5-Person Team

| Person | Roles |
|---|---|
| Person A | Backend Lead |
| Person B | ML/AI Lead |
| Person C | Frontend Lead |
| Person D | DevOps / Infrastructure |
| Person E | Team Lead / Demo Owner |

**Warning:** Five people in a hackathon creates real coordination overhead. The risk of merge conflicts, duplicated effort, and communication gaps is significant. This only works with a disciplined Team Lead who runs tight sync-ups every 3–4 hours and maintains the scope boundary ruthlessly.

---

## Communication Cadence

Regardless of team size, follow this rhythm:

| When | What | Duration |
|---|---|---|
| Start of hackathon | Kickoff: assign roles, confirm scope, agree on API contracts | 30 min |
| Every 4 hours | Standup: what's done, what's next, what's blocked | 10 min |
| Phase boundaries | Demo what's been built to the team, decide what to continue | 15 min |
| Hour 38 (feature freeze) | Full demo dry run, identify gaps, assign polish tasks | 30 min |
| Hour 44 | Final demo rehearsal | 30 min |

---

## Ownership Matrix

| Deliverable | Primary Owner | Backup |
|---|---|---|
| FastAPI application and routes | Backend Lead | ML/AI Lead |
| Database schema and migrations | Backend Lead | — |
| PHI/Secret detection pipeline | ML/AI Lead | Backend Lead |
| LLM prompt engineering | ML/AI Lead | — |
| Code review pipeline | ML/AI Lead | Backend Lead |
| Report generation pipeline | ML/AI Lead | Backend Lead |
| Angular application shell | Frontend Lead | — |
| Scan submission and results views | Frontend Lead | — |
| Report configuration and preview views | Frontend Lead | — |
| Dashboard and charts | Frontend Lead | — |
| Docker Compose and containers | DevOps | Backend Lead |
| Git hook CLI tool | Backend Lead | DevOps |
| Demo machine preparation | DevOps | Team Lead |
| Demo script and presentation | Team Lead | Everyone contributes |
| Demo data seeding | ML/AI Lead | Backend Lead |
| Scope decisions (final authority) | Team Lead | — |

---

## The Non-Negotiable Rule

**Everyone demos.** The best hackathon presentations aren't one-person shows. Each person presents the part they built. It shows depth, it shows teamwork, and it distributes the risk of presentation nerves. Plan for this from hour zero.
