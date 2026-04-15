"""POST /api/v1/reports  — queue report generation.
GET  /api/v1/reports/{id} — retrieve a report (poll for completion).
GET  /api/v1/reports/{id}/export — download report as PDF.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models.report import Report
from app.reports.aggregator import AggregationResult, aggregate_scan_data
from app.reports.pdf_export import generate_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    repository: str = Field(..., description="Repository name to aggregate")
    date_range_start: date = Field(..., description="Start date (inclusive)")
    date_range_end: date = Field(..., description="End date (inclusive)")
    audience_type: str = Field(
        default="developer",
        description="Audience: developer | manager | leadership",
    )


class ReportResponse(BaseModel):
    id: uuid.UUID
    repository: str
    date_range_start: date
    date_range_end: date
    audience_type: str
    status: str
    content: str | None
    aggregation: AggregationResult | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    id: uuid.UUID
    repository: str
    date_range_start: date
    date_range_end: date
    audience_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# POST /api/v1/reports
# ---------------------------------------------------------------------------
@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    body: ReportRequest,
    session: AsyncSession = Depends(get_session),
):
    if body.date_range_start > body.date_range_end:
        raise HTTPException(
            status_code=422, detail="date_range_start must be <= date_range_end"
        )

    # Persist report record with 'generating' status
    report = Report(
        repository=body.repository,
        date_range_start=body.date_range_start,
        date_range_end=body.date_range_end,
        audience_type=body.audience_type,
        status="generating",
        content=None,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    # Queue Celery task for LLM generation
    try:
        from app.tasks.report_task import generate_report_task
        generate_report_task.delay(
            str(report.id),
            body.repository,
            body.date_range_start.isoformat(),
            body.date_range_end.isoformat(),
            body.audience_type,
        )
    except Exception:
        # If Celery/Redis is down, generate synchronously
        from app.reports.aggregator import aggregate_scan_data as agg
        from app.reports.service import generate_report_content
        aggregation = await agg(
            session=session,
            repository=body.repository,
            start_date=body.date_range_start,
            end_date=body.date_range_end,
        )
        content = await generate_report_content(aggregation, body.audience_type)
        report.content = content
        report.status = "completed"
        await session.commit()
        await session.refresh(report)

    return ReportResponse(
        id=report.id,
        repository=report.repository,
        date_range_start=report.date_range_start,
        date_range_end=report.date_range_end,
        audience_type=report.audience_type,
        status=report.status,
        content=report.content,
        aggregation=None,
        created_at=report.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/reports/{report_id}
# ---------------------------------------------------------------------------
@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    # Auto-complete reports stuck generating for more than 5 minutes
    if report.status == "generating" and report.created_at:
        age = datetime.now(timezone.utc) - report.created_at.replace(tzinfo=timezone.utc)
        if age.total_seconds() > 300:
            report.status = "failed"
            report.content = "*Report generation timed out.*"
            await session.commit()

    # Include aggregation data when report is complete
    aggregation = None
    if report.status == "completed":
        aggregation = await aggregate_scan_data(
            session=session,
            repository=report.repository,
            start_date=report.date_range_start,
            end_date=report.date_range_end,
        )

    return ReportResponse(
        id=report.id,
        repository=report.repository,
        date_range_start=report.date_range_start,
        date_range_end=report.date_range_end,
        audience_type=report.audience_type,
        status=report.status,
        content=report.content,
        aggregation=aggregation,
        created_at=report.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/reports — list reports
# ---------------------------------------------------------------------------
@router.get("", response_model=list[ReportListItem])
async def list_reports(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Report)
        .order_by(Report.created_at.desc())
        .limit(min(limit, 100))
    )
    result = await session.execute(stmt)
    reports = result.scalars().all()
    return reports


# ---------------------------------------------------------------------------
# GET /api/v1/reports/{report_id}/export — download as PDF
# ---------------------------------------------------------------------------
@router.get("/{report_id}/export")
async def export_report(
    report_id: uuid.UUID,
    format: str = Query(default="pdf", description="Export format: pdf"),
    session: AsyncSession = Depends(get_session),
):
    """Export a completed report as a downloadable PDF document."""
    # Validate format
    if format not in ("pdf",):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported export format '{format}'. Supported: pdf",
        )

    # Fetch report
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    # Must be completed with content
    if report.status != "completed" or not report.content:
        raise HTTPException(
            status_code=409,
            detail=f"Report is not ready for export (status: {report.status})",
        )

    # Generate PDF
    try:
        pdf_bytes = generate_pdf(
            markdown_content=report.content,
            repository=report.repository,
            audience_type=report.audience_type,
            date_range_start=report.date_range_start,
            date_range_end=report.date_range_end,
            generated_at=report.created_at,
        )
    except Exception as exc:
        logger.error("PDF generation failed for report %s: %s", report_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate PDF. Please try exporting as Markdown instead.",
        )

    # Build filename
    filename = (
        f"{report.repository}-{report.audience_type}-report-"
        f"{report.date_range_start.isoformat()}-to-"
        f"{report.date_range_end.isoformat()}.pdf"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
