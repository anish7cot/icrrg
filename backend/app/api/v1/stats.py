"""GET /api/v1/stats — aggregate dashboard metrics.
GET /api/v1/stats/trends — daily scan/finding trends for charts.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models.scan import Scan
from app.db.models.scan_finding import ScanFinding
from app.api.deps import get_user_repos

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class IssueTypeCount(BaseModel):
    finding_type: str
    count: int


class StatsResponse(BaseModel):
    total_scans: int
    total_findings: int
    scans_with_findings: int
    clean_scans: int
    average_risk_score: float
    severity: SeverityCounts
    top_issue_types: list[IssueTypeCount]


@router.get("", response_model=StatsResponse)
async def get_stats(
    repository: str | None = Query(default=None, description="Filter by repository name"),
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    # Base filters — always scope to user's repos
    scan_filter = []
    finding_filter = []
    if repos:
        scan_filter.append(Scan.repository.in_(repos))
        finding_filter.append(ScanFinding.scan_id.in_(select(Scan.id).where(Scan.repository.in_(repos))))
    else:
        # No repos linked = no data
        return StatsResponse(
            total_scans=0, total_findings=0, scans_with_findings=0,
            clean_scans=0, average_risk_score=0.0, severity=SeverityCounts(),
            top_issue_types=[],
        )
    if repository:
        scan_filter.append(Scan.repository == repository)
        finding_filter.append(ScanFinding.scan_id.in_(select(Scan.id).where(Scan.repository == repository)))

    # Total scans
    q = select(func.count(Scan.id))
    if scan_filter:
        q = q.where(*scan_filter)
    total_scans = (await session.execute(q)).scalar() or 0

    # Average risk score
    q = select(func.coalesce(func.avg(Scan.risk_score), 0.0))
    if scan_filter:
        q = q.where(*scan_filter)
    avg_risk = (await session.execute(q)).scalar() or 0.0

    # Total findings
    q = select(func.count(ScanFinding.id))
    if finding_filter:
        q = q.where(*finding_filter)
    total_findings = (await session.execute(q)).scalar() or 0

    # Findings by severity
    q = select(ScanFinding.severity, func.count(ScanFinding.id)).group_by(ScanFinding.severity)
    if finding_filter:
        q = q.where(*finding_filter)
    severity_rows = (await session.execute(q)).all()
    severity_map = {row[0]: row[1] for row in severity_rows}
    severity = SeverityCounts(
        critical=severity_map.get("critical", 0),
        high=severity_map.get("high", 0),
        medium=severity_map.get("medium", 0),
        low=severity_map.get("low", 0),
    )

    # Scans that have at least one finding
    q = select(func.count(func.distinct(ScanFinding.scan_id)))
    if finding_filter:
        q = q.where(*finding_filter)
    scans_with_findings_count = (await session.execute(q)).scalar() or 0

    # Top issue types (top 10)
    q = (
        select(ScanFinding.finding_type, func.count(ScanFinding.id).label("cnt"))
        .group_by(ScanFinding.finding_type)
        .order_by(func.count(ScanFinding.id).desc())
        .limit(10)
    )
    if finding_filter:
        q = q.where(*finding_filter)
    top_types_rows = (await session.execute(q)).all()
    top_issue_types = [
        IssueTypeCount(finding_type=row[0], count=row[1]) for row in top_types_rows
    ]

    return StatsResponse(
        total_scans=total_scans,
        total_findings=total_findings,
        scans_with_findings=scans_with_findings_count,
        clean_scans=total_scans - scans_with_findings_count,
        average_risk_score=round(float(avg_risk), 1),
        severity=severity,
        top_issue_types=top_issue_types,
    )


# ---------------------------------------------------------------------------
# Trend data for charts
# ---------------------------------------------------------------------------

class DailyTrend(BaseModel):
    date: date
    scans: int
    findings: int
    critical: int
    high: int
    medium: int
    low: int


@router.get("/trends", response_model=list[DailyTrend])
async def get_trends(
    days: int = Query(default=30, ge=1, le=365),
    repository: str | None = Query(default=None, description="Filter by repository name"),
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    """Return per-day scan & finding counts for the last *days* days."""
    if not repos:
        return []

    since = datetime.now(timezone.utc) - timedelta(days=days)
    day_col = cast(Scan.created_at, Date).label("day")

    # Scans per day — scoped to user's repos
    q = select(day_col, func.count(Scan.id)).where(Scan.created_at >= since, Scan.repository.in_(repos)).group_by(day_col).order_by(day_col)
    if repository:
        q = q.where(Scan.repository == repository)
    scan_rows = (await session.execute(q)).all()
    scan_map = {row[0]: row[1] for row in scan_rows}

    # Findings per day per severity — scoped to user's repos
    finding_day = cast(ScanFinding.created_at, Date).label("day")
    q = (
        select(finding_day, ScanFinding.severity, func.count(ScanFinding.id))
        .where(
            ScanFinding.created_at >= since,
            ScanFinding.scan_id.in_(select(Scan.id).where(Scan.repository.in_(repos))),
        )
        .group_by(finding_day, ScanFinding.severity)
        .order_by(finding_day)
    )
    if repository:
        q = q.where(ScanFinding.scan_id.in_(select(Scan.id).where(Scan.repository == repository)))
    finding_rows = (await session.execute(q)).all()

    # Pivot into per-day dicts
    sev_map: dict[date, dict[str, int]] = {}
    for row in finding_rows:
        d = row[0]
        sev_map.setdefault(d, {"critical": 0, "high": 0, "medium": 0, "low": 0})
        if row[1] in sev_map[d]:
            sev_map[d][row[1]] = row[2]

    # Build continuous date series
    all_dates = set(scan_map.keys()) | set(sev_map.keys())
    if not all_dates:
        return []

    start = min(all_dates)
    end = max(all_dates)
    result = []
    current = start
    while current <= end:
        sevs = sev_map.get(current, {"critical": 0, "high": 0, "medium": 0, "low": 0})
        result.append(DailyTrend(
            date=current,
            scans=scan_map.get(current, 0),
            findings=sevs["critical"] + sevs["high"] + sevs["medium"] + sevs["low"],
            **sevs,
        ))
        current += timedelta(days=1)

    return result
