# SecureDiff — Enhancements & Features Document

**Date:** May 11, 2026  
**Commit:** `2457600` on branch `new-features`  
**Scope:** 48 files changed | 2,991 lines added | 78 lines modified  

---

## Table of Contents

1. [Multilevel Reasoning Pipeline](#1-multilevel-reasoning-pipeline)
2. [Optimizations & Enhancements](#2-optimizations--enhancements)
3. [Metrics: Cost, Time, Resource Saved](#3-metrics-cost-time-resource-saved)
4. [Developer Scoreboard (Scientific Approach)](#4-developer-scoreboard-scientific-approach)
5. [Supporting Infrastructure](#5-supporting-infrastructure)
6. [Database Schema Changes](#6-database-schema-changes)
7. [API Reference](#7-api-reference)
8. [Frontend Changes](#8-frontend-changes)
9. [Test Coverage](#9-test-coverage)
10. [File Manifest](#10-file-manifest)

---

## 1. Multilevel Reasoning Pipeline

### Overview

The review engine was upgraded from a single-pass LLM call to a **4-level reasoning pipeline** that progressively deepens analysis based on a configurable `REASONING_LEVEL` (1–4).

### Levels

| Level | Name | Engine | What it Does |
|-------|------|--------|--------------|
| **1** | Rule-Based | Regex, Entropy, NER | Pattern matching for secrets, high-entropy strings, and PII/PHI. No LLM involved. |
| **2** | LLM + Chain-of-Thought | OpenAI-compatible API | LLM analyzes the diff using a structured 5-step reasoning chain per finding. |
| **3** | Cross-Finding Correlation | LLM (separate call) | Identifies **attack chains** — groups of findings that compound into a more severe exploit path. |
| **4** | Risk Synthesis | LLM (separate call) | Produces a **prioritized remediation roadmap** with executive-level risk assessment and architectural recommendations. |

### Level 2 — Chain-of-Thought Reasoning

The system prompt was enhanced to require step-by-step reasoning for every finding:

```
Think step-by-step for each potential finding:
1. Understand:     What does this code do? What is its purpose?
2. Attack Surface: What attack vectors does this code expose?
3. Exploitability: How could an attacker exploit this? What preconditions are needed?
4. Impact:         What is the blast radius if exploited?
5. Severity:       Rate based on exploitability × impact (CVSS-like reasoning).
```

Each finding now carries a `reasoning` field containing the LLM's thought process — providing **explainability** and **auditability** for every security verdict.

### Level 3 — Cross-Finding Correlation

A dedicated correlation engine analyzes all findings from Levels 1+2 together to identify:

- **Attack chains**: Findings that, when combined, create a more severe exploit path
- **Compounding risks**: Findings whose combined impact exceeds the sum of individual parts
- **Hidden dependencies**: Findings that enable or amplify each other

**Output format:** Each correlation produces a `CorrelatedChain` containing:
- `chain_id` — sequential identifier
- `finding_refs` — indices of the connected findings
- `combined_severity` — the escalated severity of the chain
- `attack_narrative` — 2–3 sentence narrative of the exploit path
- `compounded_risk` — description of the amplified risk

### Level 4 — Risk Synthesis

A principal-security-architect prompt synthesizes all findings + correlations into:

- `overall_risk_rating` — (critical / high / medium / low / minimal)
- `executive_summary` — 2–3 sentence posture assessment
- `remediation_priority` — ordered list with priority, effort, and impact ratings
- `architectural_recommendations` — 1–3 high-level improvements

The synthesis result is stored in the `scans.synthesis_json` JSONB column for retrieval by reports and dashboards.

### Configuration

```env
REASONING_LEVEL=2   # Default: 1=rules, 2=LLM+CoT, 3=+correlation, 4=+synthesis
```

Can also be overridden per-scan via the API request body:
```json
{ "diff_text": "...", "reasoning_level": 4 }
```

### Files Created/Modified

| File | Change |
|------|--------|
| `app/review/service.py` | Rewritten — multi-level pipeline orchestrator with `ReviewPipelineResult` |
| `app/review/correlation.py` | **New** — Level 3 correlation engine |
| `app/review/synthesis.py` | **New** — Level 4 synthesis engine |
| `app/review/prompts/system.py` | Enhanced — CoT reasoning instructions + `reasoning` field in schema |
| `app/review/prompts/correlation.py` | **New** — Level 3 threat-modeling prompt |
| `app/review/prompts/synthesis.py` | **New** — Level 4 remediation-roadmap prompt |
| `app/review/response_parser.py` | Added `reasoning` field to `ReviewFindingModel` |
| `app/llm/base.py` | Added `TokenUsage`, `LLMResponse` dataclasses, `chat()` abstract method |

---

## 2. Optimizations & Enhancements

### 2.1 Cross-Engine Finding Deduplication

**Problem:** Multiple detection engines (regex, entropy, NER, LLM) often flag the same issue, inflating finding counts.

**Solution:** A deduplication engine runs after all engines complete, using three matching criteria:
- **Same file path** — findings grouped by file
- **Line proximity** — findings within ±2 lines are candidates
- **Category overlap** — cross-engine category matching via semantic groups:

| Group | Matches Across Engines |
|-------|----------------------|
| `secret` | secret, hardcoded secret, credential |
| `injection` | injection, SQL injection, command injection, XSS |
| `transport` | insecure transport, HTTP, TLS |
| `phi` | PHI, PII, sensitive data exposure |
| `entropy` | entropy, random |

**Tie-breaking:** When duplicates are found, the finding with the **higher confidence score** is kept.

**File:** `app/review/dedup.py`

### 2.2 Diff Caching (SHA-256)

**Problem:** Identical diffs scanned repeatedly waste LLM tokens and time.

**Solution:** Each diff is hashed with SHA-256 at scan time. Before running detection:
1. Compute `diff_hash = SHA256(diff_text)`
2. Check if any scan with the same `diff_hash` completed in the last 24 hours
3. If found → return cached result immediately (cache hit)
4. If not → proceed with full analysis

The `diff_hash` column is indexed (`ix_scans_diff_hash`) for fast lookups.

**Metrics tracked:** `ScanMetrics.cache_hit` (boolean per scan), `cache_hit_rate` in summary.

### 2.3 Parallel LLM Calls

**Problem:** Large diffs are chunked into multiple segments, each requiring a separate LLM call. Sequential processing is slow.

**Solution:** Chunks are now processed in parallel using `asyncio.gather()` with a concurrency limiter:

```python
_MAX_CONCURRENT_LLM = 3  # Semaphore limit
semaphore = asyncio.Semaphore(_MAX_CONCURRENT_LLM)

async def _review_chunk(chunk):
    async with semaphore:
        return await provider.review(chunk)

tasks = [_review_chunk(chunk) for chunk in chunks]
chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 2.4 Token Usage Tracking

Every LLM call now returns a full `LLMResponse` dataclass containing:
- `findings` — parsed security findings
- `usage` — `TokenUsage(prompt_tokens, completion_tokens, total_tokens)`
- `model` — model name used
- `duration_ms` — wall-clock time of the call

Token usage is aggregated across all pipeline levels and persisted in `scan_metrics`.

### 2.5 New LLM Provider Methods

| Method | Purpose |
|--------|---------|
| `chat(messages, temperature)` | Generic chat completion returning `LLMResponse` with parsed findings + usage |
| `chat_raw(messages, temperature)` | Returns raw content string + `TokenUsage` + `duration_ms` (used by Level 3/4) |

Both methods include retry logic (up to `_MAX_RETRIES`) for rate limits and timeouts, with full error handling.

### 2.6 LLM Pricing Engine

A model pricing lookup table enables real-time cost calculation:

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|---------------------|----------------------|
| nvidia/nemotron-3-super-120b-a12b:free | $0.00 | $0.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| anthropic/claude-3.5-sonnet | $3.00 | $15.00 |
| meta-llama/llama-3.1-70b-instruct | $0.52 | $0.75 |

**Formula:** `cost = (input_tokens / 1M) × input_rate + (output_tokens / 1M) × output_rate`

**File:** `app/llm/pricing.py`

### 2.7 Timing Instrumentation

Every detection engine is now individually timed using `time.perf_counter()`:

```
scan_start → total_time_ms
  ├── regex_time_ms    (secret pattern matching)
  ├── entropy_time_ms  (Shannon entropy analysis)
  ├── ner_time_ms      (spaCy NER for PHI/PII)
  └── llm_time_ms      (LLM review calls)
```

All timings are persisted in the `scan_metrics` table per scan.

---

## 3. Metrics: Cost, Time, Resource Saved

### 3.1 NIST-Based Savings Calculator

Estimated savings use the **NIST SP 800-65** cost-of-defect model and **IBM Systems Sciences Institute** data:

| Severity | Production Fix Multiplier | Savings per Finding (base=$50) |
|----------|--------------------------|-------------------------------|
| Critical | 30× | **$1,450** |
| High | 15× | **$700** |
| Medium | 6× | **$250** |
| Low | 2× | **$50** |

**Formula:** `savings = base_cost × (production_multiplier − 1)`

The −1 accounts for the fact that fixing pre-commit still has a cost (1× baseline).

**Configurable:** `BASE_FINDING_COST_USD=50.0` in settings.

### 3.2 Scan Metrics Table

Every scan now records granular metrics in `scan_metrics`:

| Column | Type | Description |
|--------|------|-------------|
| `total_time_ms` | Integer | End-to-end scan duration |
| `regex_time_ms` | Integer | Regex engine duration |
| `entropy_time_ms` | Integer | Entropy analysis duration |
| `ner_time_ms` | Integer | NER/spaCy duration |
| `llm_time_ms` | Integer | LLM call(s) duration |
| `llm_input_tokens` | Integer | Total prompt tokens |
| `llm_output_tokens` | Integer | Total completion tokens |
| `llm_cost_usd` | Float | Calculated cost from pricing table |
| `llm_calls_count` | Integer | Number of LLM API calls |
| `reasoning_level` | Integer | Reasoning depth used (1-4) |
| `cache_hit` | Boolean | Whether diff cache was used |
| `findings_before_dedup` | Integer | Finding count before dedup |
| `findings_after_dedup` | Integer | Finding count after dedup |
| `estimated_savings_usd` | Float | NIST-based savings estimate |

### 3.3 Metrics API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/metrics/summary` | GET | Aggregated metrics (total scans, tokens, cost, savings, ROI, cache hit rate, dedup stats) |
| `/api/v1/metrics/scan/{id}` | GET | Detailed metrics for a single scan |
| `/api/v1/metrics/trends` | GET | Daily aggregated trends for charts (scans, cost, savings, tokens) |

**Summary response includes:**
- `total_scans`, `total_llm_calls`, `total_input_tokens`, `total_output_tokens`
- `total_llm_cost_usd`, `total_estimated_savings_usd`
- `avg_scan_time_ms`, `avg_llm_time_ms`
- `cache_hit_rate`
- `total_findings_before_dedup`, `total_findings_after_dedup`, `dedup_savings_count`
- `roi_multiplier` — (estimated savings ÷ LLM cost)

---

## 4. Developer Scoreboard (Scientific Approach)

### 4.1 Scoring Methodology

The developer scoreboard uses a **composite score** (0–100) derived from three scientifically-grounded sub-scores:

```
Composite = Security(40%) + Responsiveness(30%) + Improvement(30%)
```

#### Security Score (40% weight) — Based on CWE Density (MITRE)

Measures code hygiene through clean scan rate with severity penalties.

**Formula:**
```
base = (clean_scan_count / total_scans) × 100
penalty = avg_critical × 5.0 + avg_high × 3.0 + avg_medium × 1.0
security_score = clamp(base − penalty, 0, 100)
```

**Scientific basis:** CWE Density metric — defect density per unit of work, adapted as findings-per-scan. Sourced from MITRE's Common Weakness Enumeration framework.

#### Responsiveness Score (30% weight) — Based on OWASP SAMM

Measures developer engagement with security findings through feedback/triage rate.

**Formula:**
```
feedback_rate = feedback_given_count / total_findings
base = min(1.0, feedback_rate) × 100
if feedback_rate > 0.8: bonus +10
responsiveness_score = clamp(base, 0, 100)
```

**Scientific basis:** OWASP SAMM "Defect Tracking" maturity model — higher maturity requires active triage and feedback on all findings.

#### Improvement Score (30% weight) — Based on Statistical Process Control

Measures trend — whether finding density is improving versus the prior period.

**Formula:**
```
change_ratio = (previous_density − current_density) / previous_density
improvement_score = 50 + (change_ratio × 50)
```

| Scenario | Score |
|----------|-------|
| Eliminated all findings | 100 |
| No change | 50 (neutral) |
| Findings doubled | 0 |

**Scientific basis:** Statistical Process Control (SPC) — trend analysis comparing current performance against historical baseline.

#### Finding Density Calculation

Uses severity-weighted density rather than raw counts:

| Severity | Weight |
|----------|--------|
| Critical | 10.0 |
| High | 7.0 |
| Medium | 4.0 |
| Low | 1.0 |

```
weighted_density = (critical×10 + high×7 + medium×4 + low×1) / total_scans
```

### 4.2 Scoring Job

- Runs on-demand via admin API or scheduled via Celery beat
- Uses a rolling 7-day window for each period
- Compares current period density against previous period for improvement scoring
- Upsert logic — updates existing scores or creates new ones
- Rankings computed after all scores calculated (ordered by composite score DESC, critical findings ASC for tiebreaking)

### 4.3 Scoreboard API Endpoints

| Endpoint | Method | Access | Description |
|----------|--------|--------|-------------|
| `/api/v1/scoreboard` | GET | Admin/Manager | Full team leaderboard with rankings |
| `/api/v1/scoreboard/me` | GET | All users | Own score + anonymized percentile |
| `/api/v1/scoreboard/history` | GET | All users | Score trend (last 8 weeks) |
| `/api/v1/scoreboard/calculate` | POST | Admin/Manager | Trigger score recalculation |
| `/api/v1/scoreboard/methodology` | GET | All users | Full scoring methodology documentation |

### 4.4 Score Verification

Tested with known inputs:
```
Input:  10 scans, 5 findings, 7 clean, 1 critical, 2 high, 2 medium, 0 low
Output: Security=68.7, Responsiveness=60.0, Improvement=80.0, Composite=69.48
```

---

## 5. Supporting Infrastructure

### 5.1 Auth & Role System

| Feature | Implementation |
|---------|---------------|
| User roles | New `role` column: `developer` (default), `manager`, `admin` |
| JWT claims | Token now includes `role` field alongside `sub` (username) |
| Dependencies | `require_admin()` and `require_manager_or_admin()` FastAPI dependencies |
| Seed script | `seed_admin.py` now sets `role="admin"` on the default user |

### 5.2 Token Decoding Changes

**Before:** `decode_access_token()` returned `str | None` (username)  
**After:** Returns `dict | None` with `{"username": ..., "role": ...}`

All consumers updated: `get_current_user`, `optional_user`, auth endpoints.

---

## 6. Database Schema Changes

### Migration: `c8a9f2b1d3e4`

**Type:** Merge migration (parents: `5c4e5a090ea6`, `a1b2c3d4e5f6`)

#### Modified Tables

| Table | Column | Type | Description |
|-------|--------|------|-------------|
| `users` | `role` | String(20) | User role (developer/manager/admin), default "developer" |
| `scans` | `diff_hash` | String(64) | SHA-256 hash for cache lookup, indexed |
| `scans` | `reasoning_level` | Integer | Reasoning depth used (1–4), default 1 |
| `scans` | `synthesis_json` | JSONB | Level 4 synthesis output |
| `scan_findings` | `reasoning` | Text | Chain-of-thought reasoning per finding |

#### New Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `scan_metrics` | Per-scan timing, token, cost, dedup metrics | 14 metric columns + scan FK |
| `developer_scores` | Weekly developer scoring and ranking | sub-scores, density, rank, unique(user_id, period_start) |

---

## 7. API Reference

### New Endpoints

| # | Endpoint | Method | Auth | Description |
|---|----------|--------|------|-------------|
| 1 | `/api/v1/metrics/summary` | GET | User | Aggregated cost/time/savings metrics |
| 2 | `/api/v1/metrics/scan/{id}` | GET | User | Single scan detailed metrics |
| 3 | `/api/v1/metrics/trends` | GET | User | Daily metrics trends for charts |
| 4 | `/api/v1/scoreboard` | GET | Manager+ | Team leaderboard |
| 5 | `/api/v1/scoreboard/me` | GET | User | Own score + percentile |
| 6 | `/api/v1/scoreboard/history` | GET | User | Last 8 weeks score trend |
| 7 | `/api/v1/scoreboard/calculate` | POST | Manager+ | Trigger score calculation |
| 8 | `/api/v1/scoreboard/methodology` | GET | Public | Scoring methodology docs |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `POST /api/v1/scans` | Accepts optional `reasoning_level` (1-4). Returns `reasoning_level` and `synthesis_json` in response. |
| `POST /api/v1/auth/login` | Response now includes `role` field |
| `POST /api/v1/auth/register` | Response now includes `role` field |
| `GET /api/v1/auth/me` | Response now includes `role` field |

---

## 8. Frontend Changes

### New Components

| Component | Description |
|-----------|-------------|
| `ScoreboardComponent` | Full-page scoreboard with score cards, history table, leaderboard (admin view), and methodology documentation |

### New Services

| Service | Endpoints Used |
|---------|---------------|
| `MetricsService` | `getSummary()`, `getScanMetrics()`, `getTrends()` |
| `ScoreboardService` | `getLeaderboard()`, `getMyScore()`, `getHistory()`, `triggerCalculation()`, `getMethodology()` |

### Modified Services

| Service | Changes |
|---------|---------|
| `AuthService` | Added `ROLE_KEY` localStorage persistence, `role$` BehaviorSubject, `getRole()`, `isAdmin()`, `isManagerOrAdmin()` methods |

### New Guards

| Guard | Purpose |
|-------|---------|
| `roleGuard` | Checks `isManagerOrAdmin()` for protected routes |

### Navigation

- Added **"Scoreboard"** nav item with `leaderboard` Material icon in the sidebar

### Routing

```typescript
{ path: 'scoreboard', component: ScoreboardComponent, canActivate: [authGuard] }
```

---

## 9. Test Coverage

- **160 tests passing**, 0 failures, 4 skipped
- `test_review_pipeline.py` updated to handle `ReviewPipelineResult` return type
- All single-chunk tests now mock `provider.chat()` → `LLMResponse` (instead of old `provider.review()`)
- Multi-chunk tests continue using `provider.review()` (parallel path)
- Empty diff, no findings, approximate line, and invalid finding tests all adapted

---

## 10. File Manifest

### New Files (25)

| File | Lines | Purpose |
|------|-------|---------|
| `app/review/correlation.py` | 116 | Level 3 correlation engine |
| `app/review/synthesis.py` | 156 | Level 4 synthesis engine |
| `app/review/dedup.py` | 99 | Cross-engine finding deduplication |
| `app/review/prompts/correlation.py` | 33 | Level 3 prompt template |
| `app/review/prompts/synthesis.py` | 44 | Level 4 prompt template |
| `app/scoring/calculator.py` | 218 | Scientific scoring engine |
| `app/scoring/job.py` | 214 | Periodic scoring job |
| `app/metrics/savings_calculator.py` | 56 | NIST-based savings calculator |
| `app/llm/pricing.py` | 45 | Model pricing lookup table |
| `app/utils/timing.py` | 47 | Timing instrumentation utilities |
| `app/api/v1/metrics.py` | 200 | Metrics API endpoints |
| `app/api/v1/scoreboard.py` | 279 | Scoreboard API endpoints |
| `app/db/models/scan_metrics.py` | 33 | ScanMetrics ORM model |
| `app/db/models/developer_score.py` | 51 | DeveloperScore ORM model |
| `alembic/versions/c8a9f2b1d3e4_...py` | 96 | Database migration |
| `cleanup_old_data.py` | 39 | One-time data cleanup script |
| `app/scoring/__init__.py` | 0 | Package init |
| `app/metrics/__init__.py` | 0 | Package init |
| `app/utils/__init__.py` | 0 | Package init |
| `frontend/.../scoreboard.component.ts` | 101 | Scoreboard page logic |
| `frontend/.../scoreboard.component.html` | 172 | Scoreboard page template |
| `frontend/.../scoreboard.component.scss` | 197 | Scoreboard page styles |
| `frontend/.../metrics.service.ts` | 71 | Metrics API service |
| `frontend/.../scoreboard.service.ts` | 92 | Scoreboard API service |
| `frontend/.../role.guard.ts` | 18 | Role-based route guard |

### Modified Files (23)

| File | Insertions | Purpose of Change |
|------|------------|-------------------|
| `app/review/service.py` | +174 | Rewritten as multi-level pipeline |
| `app/tasks/review_task.py` | +100 | Persist metrics, synthesis, reasoning |
| `app/api/v1/scans.py` | +87 | Caching, timing, dedup, metrics persistence |
| `app/llm/openai_provider.py` | +86 | `chat()`, `chat_raw()`, usage extraction |
| `app/llm/mock_provider.py` | +40 | Mock `chat()` for Level 3/4 |
| `app/api/deps.py` | +28 | Role guards, token decoding update |
| `app/llm/base.py` | +24 | `TokenUsage`, `LLMResponse`, `chat()` abstract |
| `app/review/prompts/system.py` | +14 | CoT reasoning instructions |
| `app/api/v1/auth.py` | +12 | Role in responses |
| `app/api/auth.py` | +13 | Role in JWT, dict return from decode |
| `app/config.py` | +6 | `REASONING_LEVEL`, `BASE_FINDING_COST_USD` |
| `app/db/models/scan.py` | +6 | `diff_hash`, `reasoning_level`, `synthesis_json` |
| `app/main.py` | +4 | Register metrics + scoreboard routers |
| `app/db/models/__init__.py` | +3 | Export new models |
| `cli/config.py` | +8 | Blocking policy defaults |
| `seed_admin.py` | +8 | Admin role on seed user |
| `tests/test_review_pipeline.py` | +45 | `ReviewPipelineResult` adaptation |
| `frontend/.../auth.service.ts` | +25 | Role tracking |
| `frontend/.../app.component.html` | +4 | Scoreboard nav item |
| `frontend/.../app.routes.ts` | +2 | Scoreboard route |
| `app/db/models/user.py` | +1 | `role` column |
| `app/db/models/scan_finding.py` | +1 | `reasoning` column |
| `app/review/response_parser.py` | +1 | `reasoning` field |

---

*Document generated from commit `2457600` — SecureDiff (ICRRG) project.*
