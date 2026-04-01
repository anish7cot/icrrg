"""Celery task — generate LLM report in the background."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime

from sqlalchemy import create_engine, text

from app.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _sync_db_url() -> str:
    return settings.DATABASE_URL.replace("+asyncpg", "")


async def _generate(report_id: str, repository: str, start: date, end: date, audience: str) -> str:
    """Run the async aggregation + LLM pipeline."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.reports.aggregator import aggregate_scan_data
    from app.reports.service import generate_report_content

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with sf() as session:
            aggregation = await aggregate_scan_data(session, repository, start, end)

        content = await generate_report_content(aggregation, audience)
        return content
    finally:
        await engine.dispose()


def _persist_report(report_id: str, content: str, status: str) -> None:
    """Update the report row with generated content using sync driver."""
    engine = create_engine(_sync_db_url())
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE reports SET content = :content, status = :status WHERE id = :id"),
                {"content": content, "status": status, "id": uuid.UUID(report_id)},
            )
    finally:
        engine.dispose()


@celery_app.task(name="generate_report", bind=True, max_retries=1)
def generate_report_task(
    self,
    report_id: str,
    repository: str,
    date_range_start: str,
    date_range_end: str,
    audience_type: str,
) -> dict:
    """Celery entry point — runs async pipeline, persists result synchronously."""
    logger.info("Starting report generation for %s (audience=%s)", report_id, audience_type)
    try:
        start = date.fromisoformat(date_range_start)
        end = date.fromisoformat(date_range_end)

        content = asyncio.run(_generate(report_id, repository, start, end, audience_type))

        _persist_report(report_id, content, "completed")
        logger.info("Report %s generated successfully (%d chars)", report_id, len(content))
        return {"report_id": report_id, "status": "completed", "length": len(content)}

    except Exception as exc:
        logger.error("Report generation failed for %s: %s", report_id, exc)
        try:
            _persist_report(report_id, f"*Report generation failed: {exc}*", "failed")
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=10)
