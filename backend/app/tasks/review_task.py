"""Celery task — run LLM code review in the background."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as SyncSession

from app.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _sync_db_url() -> str:
    """Convert async DB URL to sync (psycopg2) for use in Celery worker."""
    return settings.DATABASE_URL.replace("+asyncpg", "")


def _persist_findings_sync(scan_id: str, findings: list, pipeline_result) -> int:
    """Persist LLM findings, metrics, and mark scan completed using sync DB operations."""
    from app.llm.pricing import calculate_cost
    from app.metrics.savings_calculator import calculate_scan_savings

    engine = create_engine(_sync_db_url())
    try:
        with engine.begin() as conn:
            scan_uuid = uuid.UUID(scan_id)

            # Check scan exists
            row = conn.execute(
                text("SELECT risk_score FROM scans WHERE id = :id"),
                {"id": scan_uuid},
            ).fetchone()
            if row is None:
                logger.error("Scan %s not found", scan_id)
                return 0

            existing_score = row[0] or 0.0

            severity_weight = {
                "critical": 10.0, "high": 7.0, "medium": 4.0, "low": 1.0,
            }

            # Insert findings
            for f in findings:
                conn.execute(
                    text("""
                        INSERT INTO scan_findings
                            (id, scan_id, finding_type, severity, message, file_path, line_number, confidence, reasoning)
                        VALUES
                            (:id, :scan_id, :finding_type, :severity, :message, :file_path, :line_number, :confidence, :reasoning)
                    """),
                    {
                        "id": uuid.uuid4(),
                        "scan_id": scan_uuid,
                        "finding_type": f.rule_name,
                        "severity": f.severity,
                        "message": f"{f.description} — {f.suggestion}",
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "confidence": f.confidence,
                        "reasoning": f.reasoning or None,
                    },
                )

            # Update risk score + status + synthesis
            review_score = sum(severity_weight.get(f.severity, 1.0) for f in findings)
            new_score = min(10.0, round(existing_score + review_score, 2))

            synthesis_json = None
            if pipeline_result.synthesis:
                s = pipeline_result.synthesis
                synthesis_json = json.dumps({
                    "overall_risk_rating": s.overall_risk_rating,
                    "executive_summary": s.executive_summary,
                    "remediation_priority": [
                        {"priority": r.priority, "finding_refs": r.finding_refs,
                         "action": r.action, "effort": r.effort, "impact": r.impact}
                        for r in s.remediation_priority
                    ],
                    "architectural_recommendations": s.architectural_recommendations,
                })

            conn.execute(
                text("""
                    UPDATE scans
                    SET risk_score = :score, status = 'completed',
                        reasoning_level = :level, synthesis_json = :synthesis
                    WHERE id = :id
                """),
                {
                    "score": new_score,
                    "id": scan_uuid,
                    "level": pipeline_result.reasoning_level_executed,
                    "synthesis": synthesis_json,
                },
            )

            # Persist scan metrics
            usage = pipeline_result.total_usage
            llm_cost = calculate_cost(
                settings.REVIEW_MODEL,
                usage.prompt_tokens,
                usage.completion_tokens,
            )

            # Get all findings for savings calculation (existing + new)
            all_findings_data = [{"severity": f.severity} for f in findings]
            estimated_savings = calculate_scan_savings(all_findings_data)

            conn.execute(
                text("""
                    INSERT INTO scan_metrics
                        (id, scan_id, total_time_ms, llm_time_ms, llm_input_tokens,
                         llm_output_tokens, llm_cost_usd, llm_calls_count,
                         reasoning_level, findings_after_dedup, estimated_savings_usd)
                    VALUES
                        (:id, :scan_id, :total_time_ms, :llm_time_ms, :llm_input_tokens,
                         :llm_output_tokens, :llm_cost_usd, :llm_calls_count,
                         :reasoning_level, :findings_after_dedup, :estimated_savings_usd)
                """),
                {
                    "id": uuid.uuid4(),
                    "scan_id": scan_uuid,
                    "total_time_ms": pipeline_result.llm_total_duration_ms,
                    "llm_time_ms": pipeline_result.llm_total_duration_ms,
                    "llm_input_tokens": usage.prompt_tokens,
                    "llm_output_tokens": usage.completion_tokens,
                    "llm_cost_usd": llm_cost,
                    "llm_calls_count": pipeline_result.llm_calls_count,
                    "reasoning_level": pipeline_result.reasoning_level_executed,
                    "findings_after_dedup": len(findings),
                    "estimated_savings_usd": estimated_savings,
                },
            )

        return len(findings)
    finally:
        engine.dispose()


def _mark_completed_sync(scan_id: str) -> None:
    """Fallback: mark scan completed even if review failed."""
    engine = create_engine(_sync_db_url())
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE scans SET status = 'completed' WHERE id = :id"),
                {"id": uuid.UUID(scan_id)},
            )
    finally:
        engine.dispose()


@celery_app.task(name="run_code_review", bind=True, max_retries=1)
def run_code_review_task(self, scan_id: str, diff_text: str, reasoning_level: int | None = None) -> dict:
    """Celery task entry point — runs the async LLM call, then sync DB persist."""
    logger.info("Starting code review for scan %s (level=%s)", scan_id, reasoning_level)
    try:
        from app.review.service import run_code_review
        pipeline_result = asyncio.run(run_code_review(diff_text, reasoning_level))
        findings = pipeline_result.findings

        count = _persist_findings_sync(scan_id, findings, pipeline_result)
        logger.info("Code review complete for scan %s: %d findings (level %d)",
                    scan_id, count, pipeline_result.reasoning_level_executed)
        return {"scan_id": scan_id, "findings_count": count,
                "reasoning_level": pipeline_result.reasoning_level_executed}
    except Exception as exc:
        logger.error("Code review failed for scan %s: %s", scan_id, exc)
        try:
            _mark_completed_sync(scan_id)
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=5)
