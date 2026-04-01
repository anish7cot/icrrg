"""Report generation pipeline — aggregate → prompt → LLM → store."""

from __future__ import annotations

import logging
from datetime import date

import openai

from app.config import settings
from app.reports.aggregator import AggregationResult, aggregate_scan_data
from app.reports.prompt_builder import build_report_prompt

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_TIMEOUT_SECONDS = 180


async def _call_llm(prompt: str) -> str:
    """Send the rendered prompt to the LLM and return the markdown report."""
    if settings.LLM_PROVIDER == "mock":
        return _mock_report(prompt)

    client = openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        timeout=_TIMEOUT_SECONDS,
    )

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=settings.REVIEW_MODEL,
                messages=[
                    {"role": "system", "content": "You are a security report writer. Output your report in clean Markdown format."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content or ""
        except (openai.RateLimitError, openai.APITimeoutError) as exc:
            last_error = exc
            if attempt < _MAX_RETRIES:
                logger.warning("LLM call attempt %d failed: %s — retrying", attempt + 1, exc)
                continue
        except openai.APIError as exc:
            last_error = exc
            logger.error("LLM API error: %s", exc)
            break

    logger.error("Report LLM call failed: %s", last_error)
    return f"*Report generation failed — LLM unavailable. Error: {last_error}*"


def _mock_report(prompt: str) -> str:
    """Return a pre-written sample report based on audience cues in the prompt."""
    if "technical security report" in prompt.lower():
        return _MOCK_DEVELOPER
    elif "delivery and risk summary" in prompt.lower():
        return _MOCK_MANAGER
    else:
        return _MOCK_LEADERSHIP


async def generate_report_content(
    aggregation: AggregationResult,
    audience_type: str,
) -> str:
    """Full pipeline: build prompt from aggregation → call LLM → return markdown."""
    prompt = build_report_prompt(aggregation, audience_type)
    logger.info(
        "Generating %s report (%d chars prompt, %d findings)",
        audience_type, len(prompt), aggregation.total_findings,
    )
    content = await _call_llm(prompt)
    logger.info("Report generated: %d chars", len(content))
    return content


# ---------------------------------------------------------------------------
# Mock reports for each audience
# ---------------------------------------------------------------------------

_MOCK_DEVELOPER = """# Security Scan Report — Developer View

## Executive Summary

Over the past 2 weeks, **80 commits** were scanned across the `acme-webapp` repository, yielding **285 security findings**. The average risk score is **9.14/10**, indicating a high-risk codebase that requires immediate remediation.

## Critical & High Findings

- **Exposed Credentials** (29 instances): AWS keys, GitHub tokens, and generic API keys found in `src/config/settings.py`, `.env.example`, and `src/auth/jwt_utils.py`. **Action:** Rotate all exposed keys immediately. Add `.env` to `.gitignore` and migrate secrets to a vault.
- **SQL Injection** (18 instances): String concatenation used in `src/api/payments.py` and `src/db/migrations/002_add_users.sql`. **Action:** Use parameterized queries exclusively.
- **XSS Vulnerabilities** (16 instances): Unsanitized user input rendered in `src/services/notification.py`. **Action:** Implement output encoding middleware.
- **Missing Authentication** (15 instances): Several endpoints in `src/api/` lack auth decorators. **Action:** Add `@require_auth` to all non-public routes.

## Medium & Low Findings

- 19 high-entropy strings flagged as potential secrets — review and rotate if confirmed
- 25 PII instances (emails, phone numbers) in source — implement data masking
- 13 weak cryptography usages (MD5, DES) — upgrade to bcrypt/AES-256

## Hotspot Files

1. `src/services/email_service.py` — 26 findings (7 critical)
2. `src/utils/crypto.py` — 25 findings (weak algorithms)
3. `.env.example` — 25 findings (9 critical credential exposures)
4. `src/auth/jwt_utils.py` — 22 findings (key management issues)
5. `src/api/health.py` — 22 findings (exposed debug info)

## Recommended Next Steps

1. **Immediate:** Rotate all exposed credentials and API keys
2. **This sprint:** Implement parameterized queries across all DB access
3. **Next sprint:** Add pre-commit secret scanning hooks
4. **Backlog:** Migrate to a secrets management solution (HashiCorp Vault)
"""

_MOCK_MANAGER = """# Security & Delivery Summary — Engineering Manager View

## Sprint Security Summary

The `acme-webapp` repository shows **elevated security risk** with an average score of 9.14/10 across 80 scanned commits. The codebase has accumulated 285 findings, with 57 critical and 97 high-severity issues. This represents a significant remediation backlog that will impact delivery velocity if not addressed.

## Risk Heatmap

| Module | Findings | Critical | High | Recommendation |
|--------|----------|----------|------|----------------|
| Email Service | 26 | 7 | 5 | Dedicated security sprint needed |
| Crypto Utilities | 25 | 1 | 8 | Algorithm upgrade task |
| Configuration | 25 | 9 | 4 | Immediate secrets rotation |

## Issue Category Trends

1. **Hardcoded credentials** (29 instances) — The team lacks a secrets management workflow. Recommend adopting HashiCorp Vault or AWS Secrets Manager.
2. **Input validation gaps** (34 instances of injection/XSS) — Systematic gap in input handling. Consider a team training session on secure coding.
3. **Open redirects** (21 instances) — Suggest adding URL validation middleware as a shared utility.

## Velocity Impact

Estimated remediation effort: **57 critical × 2h + 97 high × 1h = 211 engineer-hours** (~5.3 engineer-weeks). Recommend allocating 2 engineers for a focused 3-week security sprint.

## Recommended Actions

1. Schedule a **security triage** meeting this week to prioritize critical findings
2. Allocate **2 engineers** to a security remediation sprint
3. Implement **pre-commit hooks** for secret scanning (1-day setup)
4. Schedule **secure coding training** for the team (half-day)
5. Set up **automated security scanning** in CI/CD pipeline
"""

_MOCK_LEADERSHIP = """# Security Posture Briefing — Executive Summary

## Release Readiness Assessment

The `acme-webapp` product **requires remediation before release**. Our automated security review of 80 recent code changes identified 57 critical vulnerabilities that pose immediate risk to customer data and system integrity. The overall security score is 9% (where 100% is fully secure).

## Top 3 Business Risks

1. **Customer Data Exposure**: We found credentials and access keys embedded directly in the application code. If this code were accessed by unauthorized parties, it could lead to a data breach affecting customer accounts. **Impact:** Potential regulatory penalties and loss of customer trust.

2. **Compliance Exposure**: Personal information (email addresses, phone numbers) was found stored in application logs. This creates exposure under GDPR and HIPAA regulations. **Impact:** Potential fines up to 4% of annual revenue under GDPR.

3. **Application Vulnerability**: Multiple entry points exist where malicious users could manipulate the application to access unauthorized data. **Impact:** Risk of unauthorized data access and service disruption.

## Security Investment Recommendation

Implement an **automated security scanning platform** integrated into the development workflow. This one-time investment would catch 80% of the issues found in this review before they enter the codebase, reducing remediation costs by an estimated 5x.

## Confidence Level

**High** — This assessment is based on comprehensive automated scanning of all 80 code changes in the review period, covering credential exposure, code vulnerabilities, and data privacy issues.
"""
