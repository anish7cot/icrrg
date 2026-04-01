"""Celery task — run LLM code review in the background."""

from __future__ import annotations

import asyncio
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


def _persist_findings_sync(scan_id: str, findings: list) -> int:
    """Persist LLM findings and mark scan completed using sync DB operations."""
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
                            (id, scan_id, finding_type, severity, message, file_path, line_number, confidence)
                        VALUES
                            (:id, :scan_id, :finding_type, :severity, :message, :file_path, :line_number, :confidence)
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
                    },
                )

            # Update risk score + status
            review_score = sum(severity_weight.get(f.severity, 1.0) for f in findings)
            new_score = min(10.0, round(existing_score + review_score, 2))
            conn.execute(
                text("UPDATE scans SET risk_score = :score, status = 'completed' WHERE id = :id"),
                {"score": new_score, "id": scan_uuid},
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
def run_code_review_task(self, scan_id: str, diff_text: str) -> dict:
    """Celery task entry point — runs the async LLM call, then sync DB persist."""
    logger.info("Starting code review for scan %s", scan_id)
    try:
        # Only the LLM call needs async; DB ops are sync
        from app.review.service import run_code_review
        findings = asyncio.run(run_code_review(diff_text))

        count = _persist_findings_sync(scan_id, findings)
        logger.info("Code review complete for scan %s: %d findings", scan_id, count)
        return {"scan_id": scan_id, "findings_count": count}
    except Exception as exc:
        logger.error("Code review failed for scan %s: %s", scan_id, exc)
        try:
            _mark_completed_sync(scan_id)
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=5)
