"""Commit-history aggregation service for report generation."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import date, datetime

from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.scan import Scan
from app.db.models.scan_finding import ScanFinding


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class SeverityBreakdown(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class FileGroupSummary(BaseModel):
    file_path: str
    finding_count: int
    severity_breakdown: SeverityBreakdown


class FindingTypeCount(BaseModel):
    finding_type: str
    count: int


class AggregationResult(BaseModel):
    repository: str
    date_range_start: date
    date_range_end: date
    total_scans: int
    total_findings: int
    severity_breakdown: SeverityBreakdown
    top_files: list[FileGroupSummary]
    top_finding_types: list[FindingTypeCount]
    average_risk_score: float
    max_risk_score: float
    scans_by_status: dict[str, int]


# ---------------------------------------------------------------------------
# Aggregation query
# ---------------------------------------------------------------------------

async def aggregate_scan_data(
    session: AsyncSession,
    repository: str,
    start_date: date,
    end_date: date,
) -> AggregationResult:
    """Query scans within a date range and aggregate findings."""

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Fetch scans with findings in the date range
    stmt = (
        select(Scan)
        .options(selectinload(Scan.findings))
        .where(
            Scan.repository == repository,
            Scan.created_at >= start_dt,
            Scan.created_at <= end_dt,
        )
        .order_by(Scan.created_at.desc())
    )
    result = await session.execute(stmt)
    scans = result.scalars().all()

    # Collect all findings
    all_findings: list[ScanFinding] = []
    for scan in scans:
        all_findings.extend(scan.findings)

    # Severity breakdown
    sev_counter = Counter(f.severity for f in all_findings)
    severity = SeverityBreakdown(
        critical=sev_counter.get("critical", 0),
        high=sev_counter.get("high", 0),
        medium=sev_counter.get("medium", 0),
        low=sev_counter.get("low", 0),
    )

    # Group by file path
    file_counter: dict[str, list[ScanFinding]] = {}
    for f in all_findings:
        path = f.file_path or "(unknown)"
        file_counter.setdefault(path, []).append(f)

    top_files = sorted(
        [
            FileGroupSummary(
                file_path=path,
                finding_count=len(findings),
                severity_breakdown=SeverityBreakdown(
                    critical=sum(1 for f in findings if f.severity == "critical"),
                    high=sum(1 for f in findings if f.severity == "high"),
                    medium=sum(1 for f in findings if f.severity == "medium"),
                    low=sum(1 for f in findings if f.severity == "low"),
                ),
            )
            for path, findings in file_counter.items()
        ],
        key=lambda x: x.finding_count,
        reverse=True,
    )[:20]

    # Top finding types
    type_counter = Counter(f.finding_type for f in all_findings)
    top_finding_types = [
        FindingTypeCount(finding_type=ft, count=c)
        for ft, c in type_counter.most_common(15)
    ]

    # Risk scores
    risk_scores = [s.risk_score for s in scans if s.risk_score is not None]
    avg_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
    max_risk = max(risk_scores) if risk_scores else 0.0

    # Scans by status
    status_counter = Counter(s.status for s in scans)

    return AggregationResult(
        repository=repository,
        date_range_start=start_date,
        date_range_end=end_date,
        total_scans=len(scans),
        total_findings=len(all_findings),
        severity_breakdown=severity,
        top_files=top_files,
        top_finding_types=top_finding_types,
        average_risk_score=avg_risk,
        max_risk_score=max_risk,
        scans_by_status=dict(status_counter),
    )
