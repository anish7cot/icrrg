"""POST /api/v1/scans  — submit a diff for scanning.
GET  /api/v1/scans/{id} — retrieve a past scan with findings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.db.models.scan import Scan
from app.db.models.scan_finding import ScanFinding

from app.api.deps import get_current_user, get_user_repos, ensure_user_project
from app.db.models.user import User

from app.git.diff_parser import parse_unified_diff
from app.detection.regex_engine import scan_diff_for_secrets
from app.detection.entropy import scan_diff_for_entropy
from app.detection.ner_pipeline import scan_diff_for_phi
from app.detection.sanitizer import sanitize_diff

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])

MAX_DIFF_SIZE = 5 * 1024 * 1024  # 5 MB


# ---------------------------------------------------------------------------
# GET /api/v1/scans/repositories — distinct repo names for project selector
# ---------------------------------------------------------------------------
@router.get("/repositories", response_model=list[str])
async def list_repositories(
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    return repos

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    diff_text: str = Field(..., description="Raw unified diff text")
    repository: str = Field(default="manual-paste", description="Repository name or identifier")
    commit_hash: str | None = Field(default=None, description="Commit hash (optional)")


class FindingResponse(BaseModel):
    id: uuid.UUID
    finding_type: str
    severity: str
    message: str
    file_path: str | None
    line_number: int | None
    confidence: float | None

    model_config = {"from_attributes": True}


class ScanResponse(BaseModel):
    id: uuid.UUID
    repository: str
    commit_hash: str | None
    status: str
    risk_score: float | None
    findings: list[FindingResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanSummaryResponse(BaseModel):
    id: uuid.UUID
    repository: str
    status: str
    risk_score: float | None
    finding_count: int
    created_at: datetime


class ScanNotification(BaseModel):
    """Lightweight payload returned by the polling endpoint."""
    scan_id: uuid.UUID
    status: str
    finding_count: int
    risk_score: float | None
    timestamp: datetime


# ---------------------------------------------------------------------------
# Severity → numeric weight for risk score
# ---------------------------------------------------------------------------
_SEVERITY_WEIGHT = {
    "critical": 10.0,
    "high": 7.0,
    "medium": 4.0,
    "low": 1.0,
}


def _compute_risk_score(findings_data: list[dict]) -> float:
    """Compute 0-10 risk score from findings."""
    if not findings_data:
        return 0.0
    total = sum(_SEVERITY_WEIGHT.get(f["severity"], 1.0) for f in findings_data)
    # Cap at 10
    return min(10.0, round(total, 2))


# ---------------------------------------------------------------------------
# POST /api/v1/scans
# ---------------------------------------------------------------------------
@router.post("", response_model=ScanResponse, status_code=201)
async def create_scan(
    body: ScanRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # Size guard
    if len(body.diff_text.encode("utf-8")) > MAX_DIFF_SIZE:
        raise HTTPException(status_code=413, detail="Diff text exceeds 5 MB limit")

    # 1. Parse diff
    parsed_diff = parse_unified_diff(body.diff_text)

    # 2. Run all detection engines
    secret_findings = scan_diff_for_secrets(parsed_diff)
    entropy_findings = scan_diff_for_entropy(parsed_diff)
    phi_findings = scan_diff_for_phi(parsed_diff)

    # 3. Normalise into a flat list of dicts for DB storage
    all_findings: list[dict] = []

    for f in secret_findings:
        all_findings.append({
            "finding_type": f"secret:{f.rule_name}",
            "severity": f.severity,
            "message": f"{f.description} — {f.matched_text}",
            "file_path": f.file_path,
            "line_number": f.line_number,
            "confidence": f.confidence,
        })

    for f in entropy_findings:
        all_findings.append({
            "finding_type": f"entropy:{f.rule_name}",
            "severity": f.severity,
            "message": f"{f.description} — {f.matched_text}",
            "file_path": f.file_path,
            "line_number": f.line_number,
            "confidence": f.confidence,
        })

    for f in phi_findings:
        all_findings.append({
            "finding_type": f"phi:{f.rule_name}",
            "severity": f.severity,
            "message": f"{f.description} — {f.matched_text}",
            "file_path": f.file_path,
            "line_number": f.line_number,
            "confidence": f.confidence,
        })

    risk_score = _compute_risk_score(all_findings)

    # 4. Persist scan + findings (status = "reviewing" while LLM runs)
    scan = Scan(
        repository=body.repository,
        commit_hash=body.commit_hash,
        status="reviewing",
        risk_score=risk_score,
    )
    session.add(scan)
    await session.flush()  # get scan.id

    for fd in all_findings:
        session.add(ScanFinding(scan_id=scan.id, **fd))

    await session.commit()
    await session.refresh(scan, attribute_names=["findings"])

    # Auto-link this repository to the authenticated user
    await ensure_user_project(user.id, body.repository, session)
    await session.commit()

    # 5. Queue async code review via Celery (with sanitized diff)
    sanitized = sanitize_diff(body.diff_text)
    try:
        from app.tasks.review_task import run_code_review_task
        run_code_review_task.delay(str(scan.id), sanitized)
    except Exception:
        # If Celery/Redis is down, mark completed so UI doesn't hang
        scan.status = "completed"
        await session.commit()

    return scan


# ---------------------------------------------------------------------------
# GET /api/v1/scans/poll  — lightweight polling for dashboard updates
# ---------------------------------------------------------------------------
@router.get("/poll", response_model=list[ScanNotification])
async def poll_scans(
    since: datetime | None = None,
    repository: str | None = None,
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    """Return scan notifications created after *since*.

    The frontend can call this every few seconds with the timestamp of the
    last notification it received.  If *since* is omitted the 10 most recent
    scans are returned.
    """
    stmt = select(Scan).options(selectinload(Scan.findings))

    # Scope to user's repos
    if repos:
        stmt = stmt.where(Scan.repository.in_(repos))
    else:
        stmt = stmt.where(Scan.id == None)  # no repos = no results  # noqa: E711

    if since is not None:
        stmt = stmt.where(Scan.created_at > since)
    if repository:
        stmt = stmt.where(Scan.repository == repository)

    stmt = stmt.order_by(Scan.created_at.desc()).limit(50)

    result = await session.execute(stmt)
    scans = result.scalars().all()
    return [
        ScanNotification(
            scan_id=s.id,
            status=s.status,
            finding_count=len(s.findings),
            risk_score=s.risk_score,
            timestamp=s.created_at,
        )
        for s in scans
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/scans/{scan_id}
# ---------------------------------------------------------------------------
@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: uuid.UUID,
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Scan)
        .options(selectinload(Scan.findings))
        .where(Scan.id == scan_id)
    )
    # Scope to user's repos
    if repos:
        stmt = stmt.where(Scan.repository.in_(repos))
    result = await session.execute(stmt)
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Auto-complete scans stuck in "reviewing" for more than 5 minutes
    if scan.status == "reviewing" and scan.created_at:
        age = datetime.now(timezone.utc) - scan.created_at.replace(tzinfo=timezone.utc)
        if age.total_seconds() > 300:  # 5 minutes
            scan.status = "completed"
            await session.commit()
            await session.refresh(scan, attribute_names=["findings"])

    return scan


# ---------------------------------------------------------------------------
# GET /api/v1/scans  — list recent scans
# ---------------------------------------------------------------------------
@router.get("", response_model=list[ScanSummaryResponse])
async def list_scans(
    limit: int = 20,
    repository: str | None = None,
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Scan)
        .options(selectinload(Scan.findings))
        .order_by(Scan.created_at.desc())
        .limit(min(limit, 100))
    )
    # Scope to user's repos
    if repos:
        stmt = stmt.where(Scan.repository.in_(repos))
    else:
        stmt = stmt.where(Scan.id == None)  # noqa: E711
    if repository:
        stmt = stmt.where(Scan.repository == repository)
    result = await session.execute(stmt)
    scans = result.scalars().all()
    return [
        ScanSummaryResponse(
            id=s.id,
            repository=s.repository,
            status=s.status,
            risk_score=s.risk_score,
            finding_count=len(s.findings),
            created_at=s.created_at,
        )
        for s in scans
    ]
