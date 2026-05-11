"""GET /api/v1/metrics — cost, time, and resource savings metrics."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_repos
from app.db.models.scan import Scan
from app.db.models.scan_metrics import ScanMetrics
from app.db.models.user import User
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MetricsSummary(BaseModel):
    total_scans: int = 0
    total_llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_llm_cost_usd: float = 0.0
    total_estimated_savings_usd: float = 0.0
    avg_scan_time_ms: float = 0.0
    avg_llm_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    total_findings_before_dedup: int = 0
    total_findings_after_dedup: int = 0
    dedup_savings_count: int = 0
    roi_multiplier: float = 0.0  # savings / cost


class ScanMetricsResponse(BaseModel):
    scan_id: uuid.UUID
    total_time_ms: int
    regex_time_ms: int
    entropy_time_ms: int
    ner_time_ms: int
    llm_time_ms: int
    llm_input_tokens: int
    llm_output_tokens: int
    llm_cost_usd: float
    llm_calls_count: int
    reasoning_level: int
    cache_hit: bool
    findings_before_dedup: int
    findings_after_dedup: int
    estimated_savings_usd: float

    model_config = {"from_attributes": True}


class DailyMetricsTrend(BaseModel):
    date: date
    scans: int = 0
    llm_cost_usd: float = 0.0
    estimated_savings_usd: float = 0.0
    avg_time_ms: float = 0.0
    total_tokens: int = 0


# ---------------------------------------------------------------------------
# GET /api/v1/metrics/summary
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=MetricsSummary)
async def metrics_summary(
    repository: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    """Aggregate cost, time, and savings metrics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Build base join query
    stmt = (
        select(
            func.count(ScanMetrics.id).label("total_scans"),
            func.coalesce(func.sum(ScanMetrics.llm_calls_count), 0).label("total_llm_calls"),
            func.coalesce(func.sum(ScanMetrics.llm_input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(ScanMetrics.llm_output_tokens), 0).label("total_output_tokens"),
            func.coalesce(func.sum(ScanMetrics.llm_cost_usd), 0.0).label("total_llm_cost_usd"),
            func.coalesce(func.sum(ScanMetrics.estimated_savings_usd), 0.0).label("total_savings"),
            func.coalesce(func.avg(ScanMetrics.total_time_ms), 0.0).label("avg_scan_time"),
            func.coalesce(func.avg(ScanMetrics.llm_time_ms), 0.0).label("avg_llm_time"),
            func.coalesce(func.sum(func.cast(ScanMetrics.cache_hit, Integer)), 0).label("cache_hits"),
            func.coalesce(func.sum(ScanMetrics.findings_before_dedup), 0).label("before_dedup"),
            func.coalesce(func.sum(ScanMetrics.findings_after_dedup), 0).label("after_dedup"),
        )
        .join(Scan, ScanMetrics.scan_id == Scan.id)
        .where(Scan.created_at > cutoff)
    )

    if repos:
        stmt = stmt.where(Scan.repository.in_(repos))
    if repository:
        stmt = stmt.where(Scan.repository == repository)

    result = await session.execute(stmt)
    row = result.one()

    total_scans = row.total_scans or 0
    cache_hits = row.cache_hits or 0
    total_cost = float(row.total_llm_cost_usd or 0)
    total_savings = float(row.total_savings or 0)

    return MetricsSummary(
        total_scans=total_scans,
        total_llm_calls=row.total_llm_calls or 0,
        total_input_tokens=row.total_input_tokens or 0,
        total_output_tokens=row.total_output_tokens or 0,
        total_llm_cost_usd=round(total_cost, 4),
        total_estimated_savings_usd=round(total_savings, 2),
        avg_scan_time_ms=round(float(row.avg_scan_time or 0), 1),
        avg_llm_time_ms=round(float(row.avg_llm_time or 0), 1),
        cache_hit_rate=round(cache_hits / total_scans, 3) if total_scans > 0 else 0.0,
        total_findings_before_dedup=row.before_dedup or 0,
        total_findings_after_dedup=row.after_dedup or 0,
        dedup_savings_count=(row.before_dedup or 0) - (row.after_dedup or 0),
        roi_multiplier=round(total_savings / total_cost, 1) if total_cost > 0 else 0.0,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/metrics/scan/{scan_id}
# ---------------------------------------------------------------------------
@router.get("/scan/{scan_id}", response_model=ScanMetricsResponse)
async def scan_metrics(
    scan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get detailed metrics for a specific scan."""
    stmt = select(ScanMetrics).where(ScanMetrics.scan_id == scan_id)
    result = await session.execute(stmt)
    metrics = result.scalar_one_or_none()
    if metrics is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Metrics not found for this scan")
    return metrics


# ---------------------------------------------------------------------------
# GET /api/v1/metrics/trends
# ---------------------------------------------------------------------------
@router.get("/trends", response_model=list[DailyMetricsTrend])
async def metrics_trends(
    days: int = Query(default=30, ge=1, le=365),
    repository: str | None = None,
    user: User = Depends(get_current_user),
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    """Daily metrics trends for charts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            func.date(Scan.created_at).label("scan_date"),
            func.count(ScanMetrics.id).label("scans"),
            func.coalesce(func.sum(ScanMetrics.llm_cost_usd), 0.0).label("cost"),
            func.coalesce(func.sum(ScanMetrics.estimated_savings_usd), 0.0).label("savings"),
            func.coalesce(func.avg(ScanMetrics.total_time_ms), 0.0).label("avg_time"),
            func.coalesce(func.sum(ScanMetrics.llm_input_tokens + ScanMetrics.llm_output_tokens), 0).label("tokens"),
        )
        .join(Scan, ScanMetrics.scan_id == Scan.id)
        .where(Scan.created_at > cutoff)
        .group_by(func.date(Scan.created_at))
        .order_by(func.date(Scan.created_at))
    )

    if repos:
        stmt = stmt.where(Scan.repository.in_(repos))
    if repository:
        stmt = stmt.where(Scan.repository == repository)

    result = await session.execute(stmt)
    rows = result.all()

    return [
        DailyMetricsTrend(
            date=row.scan_date,
            scans=row.scans,
            llm_cost_usd=round(float(row.cost), 4),
            estimated_savings_usd=round(float(row.savings), 2),
            avg_time_ms=round(float(row.avg_time), 1),
            total_tokens=row.tokens or 0,
        )
        for row in rows
    ]
