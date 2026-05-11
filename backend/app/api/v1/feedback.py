"""Feedback API — users mark findings as true/false positives.

POST /api/v1/findings/{finding_id}/feedback
GET  /api/v1/findings/{finding_id}/feedback
GET  /api/v1/feedback/accuracy — real-world precision from user verdicts
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models.scan import Scan
from app.db.models.scan_finding import ScanFinding
from app.db.models.finding_feedback import FindingFeedback
from app.api.deps import get_current_user, get_user_repos
from app.db.models.user import User

router = APIRouter(prefix="/api/v1/findings", tags=["feedback"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    verdict: str  # "true_positive", "false_positive", "disputed"
    comment: str | None = None
    expires_at: datetime | None = None  # optional expiration for false_positive suppression


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    scan_finding_id: uuid.UUID
    user_id: uuid.UUID
    verdict: str
    comment: str | None
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class AccuracyResponse(BaseModel):
    total_feedback: int
    true_positive: int
    false_positive: int
    disputed: int
    precision: float  # tp / (tp + fp)


_VALID_VERDICTS = {"true_positive", "false_positive", "disputed"}


# ---------------------------------------------------------------------------
# POST /api/v1/findings/{id}/feedback
# ---------------------------------------------------------------------------

@router.post("/{finding_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    finding_id: uuid.UUID,
    body: FeedbackRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if body.verdict not in _VALID_VERDICTS:
        raise HTTPException(status_code=400, detail=f"verdict must be one of {_VALID_VERDICTS}")

    # Verify finding exists
    finding = await session.get(ScanFinding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Upsert: one feedback per user per finding
    stmt = select(FindingFeedback).where(
        FindingFeedback.scan_finding_id == finding_id,
        FindingFeedback.user_id == user.id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.verdict = body.verdict
        existing.comment = body.comment
        existing.expires_at = body.expires_at
        await session.commit()
        await session.refresh(existing)
        return existing

    fb = FindingFeedback(
        scan_finding_id=finding_id,
        user_id=user.id,
        verdict=body.verdict,
        comment=body.comment,
        expires_at=body.expires_at,
    )
    session.add(fb)
    await session.commit()
    await session.refresh(fb)
    return fb


# ---------------------------------------------------------------------------
# GET /api/v1/findings/{id}/feedback
# ---------------------------------------------------------------------------

@router.get("/{finding_id}/feedback", response_model=list[FeedbackResponse])
async def get_feedback(
    finding_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(FindingFeedback).where(FindingFeedback.scan_finding_id == finding_id)
    result = await session.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /api/v1/findings/accuracy — aggregate precision from user feedback
# ---------------------------------------------------------------------------

@router.get("/accuracy", response_model=AccuracyResponse)
async def feedback_accuracy(
    session: AsyncSession = Depends(get_session),
):
    stmt = select(
        FindingFeedback.verdict,
        func.count(FindingFeedback.id),
    ).group_by(FindingFeedback.verdict)
    rows = (await session.execute(stmt)).all()
    counts = {row[0]: row[1] for row in rows}

    tp = counts.get("true_positive", 0)
    fp = counts.get("false_positive", 0)
    disputed = counts.get("disputed", 0)
    total = tp + fp + disputed

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0

    return AccuracyResponse(
        total_feedback=total,
        true_positive=tp,
        false_positive=fp,
        disputed=disputed,
        precision=round(precision, 4),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/findings/scan/{scan_id}/accuracy — accuracy for one scan
# ---------------------------------------------------------------------------

class ScanAccuracyResponse(BaseModel):
    scan_id: uuid.UUID
    total_findings: int
    reviewed_findings: int
    true_positive: int
    false_positive: int
    disputed: int
    precision: float
    review_coverage: float  # reviewed / total


@router.get("/scan/{scan_id}/accuracy", response_model=ScanAccuracyResponse)
async def scan_accuracy(
    scan_id: uuid.UUID,
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    """Accuracy metrics scoped to a single scan."""
    # Verify scan exists and user has access
    stmt = select(Scan).where(Scan.id == scan_id)
    if repos:
        stmt = stmt.where(Scan.repository.in_(repos))
    scan = (await session.execute(stmt)).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Count total findings for this scan
    total_stmt = select(func.count(ScanFinding.id)).where(ScanFinding.scan_id == scan_id)
    total_findings = (await session.execute(total_stmt)).scalar() or 0

    # Aggregate feedback for findings in this scan
    fb_stmt = (
        select(FindingFeedback.verdict, func.count(FindingFeedback.id))
        .join(ScanFinding, FindingFeedback.scan_finding_id == ScanFinding.id)
        .where(ScanFinding.scan_id == scan_id)
        .group_by(FindingFeedback.verdict)
    )
    rows = (await session.execute(fb_stmt)).all()
    counts = {row[0]: row[1] for row in rows}

    tp = counts.get("true_positive", 0)
    fp = counts.get("false_positive", 0)
    disputed = counts.get("disputed", 0)
    reviewed = tp + fp + disputed
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    coverage = reviewed / total_findings if total_findings > 0 else 0.0

    return ScanAccuracyResponse(
        scan_id=scan_id,
        total_findings=total_findings,
        reviewed_findings=reviewed,
        true_positive=tp,
        false_positive=fp,
        disputed=disputed,
        precision=round(precision, 4),
        review_coverage=round(coverage, 4),
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/findings/{id}/status — finding lifecycle transitions
# ---------------------------------------------------------------------------

_VALID_STATUSES = {"new", "confirmed", "in_progress", "resolved", "closed"}
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "new": {"confirmed", "closed"},
    "confirmed": {"in_progress", "closed"},
    "in_progress": {"resolved", "closed"},
    "resolved": {"closed", "in_progress"},  # can reopen
    "closed": {"new"},  # can reopen
}


class StatusUpdateRequest(BaseModel):
    status: str
    assigned_to: uuid.UUID | None = None


class FindingStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    assigned_to: uuid.UUID | None
    resolved_at: datetime | None
    sla_deadline: datetime | None

    model_config = {"from_attributes": True}


@router.patch("/{finding_id}/status", response_model=FindingStatusResponse)
async def update_finding_status(
    finding_id: uuid.UUID,
    body: StatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Transition a finding through its lifecycle."""
    if body.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {_VALID_STATUSES}",
        )

    finding = await session.get(ScanFinding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    current = finding.status or "new"
    allowed = _VALID_TRANSITIONS.get(current, set())
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current}' to '{body.status}'. Allowed: {allowed}",
        )

    finding.status = body.status

    if body.assigned_to is not None:
        finding.assigned_to = body.assigned_to

    if body.status == "resolved":
        from datetime import timezone
        finding.resolved_at = datetime.now(timezone.utc)
    elif body.status in ("new", "in_progress"):
        finding.resolved_at = None

    await session.commit()
    await session.refresh(finding)

    return FindingStatusResponse(
        id=finding.id,
        status=finding.status,
        assigned_to=finding.assigned_to,
        resolved_at=finding.resolved_at,
        sla_deadline=finding.sla_deadline,
    )
