"""POST /api/v1/scans  — submit a diff for scanning.
GET  /api/v1/scans/{id} — retrieve a past scan with findings.
"""

from __future__ import annotations

import hashlib
import time
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
from app.db.models.scan_metrics import ScanMetrics

from app.api.deps import get_current_user, get_user_repos, ensure_user_project
from app.db.models.user import User

from app.config import settings
from app.git.diff_parser import parse_unified_diff
from app.detection.regex_engine import scan_diff_for_secrets
from app.detection.entropy import scan_diff_for_entropy
from app.detection.ner_pipeline import scan_diff_for_phi
from app.detection.sca_engine import scan_diff_for_sca
from app.detection.sanitizer import sanitize_diff
from app.detection.cwe_mapping import enrich_finding
from app.review.dedup import deduplicate_findings
from app.metrics.savings_calculator import calculate_scan_savings

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
    reasoning_level: int | None = Field(default=None, description="Override reasoning depth (1-4)")


class FindingResponse(BaseModel):
    id: uuid.UUID
    finding_type: str
    severity: str
    message: str
    file_path: str | None
    line_number: int | None
    confidence: float | None
    reasoning: str | None = None
    cwe_id: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    status: str = "new"
    assigned_to: uuid.UUID | None = None
    resolved_at: datetime | None = None
    sla_deadline: datetime | None = None
    suppressed: bool = False

    model_config = {"from_attributes": True}


class PolicyCheckResult(BaseModel):
    blocked: bool = False
    violations_count: int = 0
    max_severity_allowed: str | None = None


class ScanResponse(BaseModel):
    id: uuid.UUID
    repository: str
    commit_hash: str | None
    status: str
    risk_score: float | None
    reasoning_level: int = 1
    synthesis_json: dict | None = None
    findings: list[FindingResponse]
    policy_check: PolicyCheckResult | None = None
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


async def _check_diff_cache(
    session: AsyncSession, diff_hash: str, user: User
) -> ScanResponse | None:
    """Check if an identical diff was scanned in the last 24 hours.

    Returns a ScanResponse if cache hit, None otherwise.
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt = (
        select(Scan)
        .options(selectinload(Scan.findings))
        .where(
            Scan.diff_hash == diff_hash,
            Scan.status == "completed",
            Scan.created_at > cutoff,
        )
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    cached = result.scalar_one_or_none()
    if cached is None:
        return None
    return cached


# ---------------------------------------------------------------------------
# Helper — annotate findings with false-positive suppression status
# ---------------------------------------------------------------------------
async def _annotate_findings_suppression(
    session: AsyncSession, findings: list
) -> list[FindingResponse]:
    """Convert ORM findings to FindingResponse, marking suppressed ones."""
    from app.db.models.finding_feedback import FindingFeedback

    if not findings:
        return []

    finding_ids = [f.id for f in findings]
    now = datetime.now(timezone.utc)

    # Fetch active false_positive verdicts (not expired)
    stmt = select(FindingFeedback.scan_finding_id).where(
        FindingFeedback.scan_finding_id.in_(finding_ids),
        FindingFeedback.verdict == "false_positive",
    )
    result = await session.execute(stmt)
    suppressed_ids: set[uuid.UUID] = set()
    for row in result.all():
        suppressed_ids.add(row[0])

    # Check expiration: remove from suppressed if expired
    if suppressed_ids:
        expired_stmt = select(FindingFeedback.scan_finding_id).where(
            FindingFeedback.scan_finding_id.in_(suppressed_ids),
            FindingFeedback.verdict == "false_positive",
            FindingFeedback.expires_at.is_not(None),
            FindingFeedback.expires_at < now,
        )
        expired_result = await session.execute(expired_stmt)
        expired_ids = {row[0] for row in expired_result.all()}
        suppressed_ids -= expired_ids

    responses = []
    for f in findings:
        resp = FindingResponse(
            id=f.id,
            finding_type=f.finding_type,
            severity=f.severity,
            message=f.message,
            file_path=f.file_path,
            line_number=f.line_number,
            confidence=f.confidence,
            reasoning=f.reasoning,
            cwe_id=f.cwe_id,
            cvss_score=f.cvss_score,
            cvss_vector=f.cvss_vector,
            status=f.status,
            assigned_to=f.assigned_to,
            resolved_at=f.resolved_at,
            sla_deadline=f.sla_deadline,
            suppressed=f.id in suppressed_ids,
        )
        responses.append(resp)
    return responses


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
    scan_start = time.perf_counter()

    # Size guard
    if len(body.diff_text.encode("utf-8")) > MAX_DIFF_SIZE:
        raise HTTPException(status_code=413, detail="Diff text exceeds 5 MB limit")

    # Compute diff hash for caching
    diff_hash = hashlib.sha256(body.diff_text.encode("utf-8")).hexdigest()

    # Check cache — same diff scanned in last 24 hours?
    cache_hit = False
    cached_scan = await _check_diff_cache(session, diff_hash, user)
    if cached_scan is not None:
        cache_hit = True
        return cached_scan

    # Determine reasoning level
    reasoning_level = body.reasoning_level if body.reasoning_level is not None else settings.REASONING_LEVEL

    # 1. Parse diff
    parsed_diff = parse_unified_diff(body.diff_text)

    # 2. Run all detection engines with timing
    t0 = time.perf_counter()
    secret_findings = scan_diff_for_secrets(parsed_diff)
    regex_time_ms = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    entropy_findings = scan_diff_for_entropy(parsed_diff)
    entropy_time_ms = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    phi_findings = scan_diff_for_phi(parsed_diff)
    ner_time_ms = int((time.perf_counter() - t0) * 1000)

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

    # 2b. SCA — check dependency manifests for known vulnerabilities
    sca_findings = scan_diff_for_sca(parsed_diff)
    for f in sca_findings:
        all_findings.append({
            "finding_type": f"sca:{f.osv_id}",
            "severity": f.severity,
            "message": f"{f.description}",
            "file_path": f.file_path,
            "line_number": f.line_number,
            "confidence": f.confidence,
        })

    # Enrich all findings with CWE / CVSS
    for fd in all_findings:
        enrich_finding(fd)

    # Deduplication
    findings_before_dedup = len(all_findings)
    all_findings = deduplicate_findings(all_findings)
    findings_after_dedup = len(all_findings)

    risk_score = _compute_risk_score(all_findings)

    # 4. Persist scan + findings (status = "reviewing" while LLM runs)
    scan = Scan(
        repository=body.repository,
        commit_hash=body.commit_hash,
        status="reviewing",
        risk_score=risk_score,
        diff_hash=diff_hash,
        reasoning_level=reasoning_level,
    )
    session.add(scan)
    await session.flush()  # get scan.id

    # Compute SLA deadlines per severity
    from datetime import timedelta
    _SLA_HOURS = {"critical": 24, "high": 72, "medium": 168, "low": 720}
    now = datetime.now(timezone.utc)
    for fd in all_findings:
        sla_h = _SLA_HOURS.get(fd["severity"], 720)
        fd["sla_deadline"] = now + timedelta(hours=sla_h)
        fd["status"] = "new"
        session.add(ScanFinding(scan_id=scan.id, **fd))

    # Persist initial timing metrics
    total_time_ms = int((time.perf_counter() - scan_start) * 1000)
    estimated_savings = calculate_scan_savings(all_findings)
    session.add(ScanMetrics(
        scan_id=scan.id,
        total_time_ms=total_time_ms,
        regex_time_ms=regex_time_ms,
        entropy_time_ms=entropy_time_ms,
        ner_time_ms=ner_time_ms,
        reasoning_level=reasoning_level,
        findings_before_dedup=findings_before_dedup,
        findings_after_dedup=findings_after_dedup,
        estimated_savings_usd=estimated_savings,
    ))

    await session.commit()
    await session.refresh(scan, attribute_names=["findings"])

    # Auto-link this repository to the authenticated user
    await ensure_user_project(user.id, body.repository, session)
    await session.commit()

    # 5. Queue async code review via Celery (with sanitized diff)
    sanitized = sanitize_diff(body.diff_text)
    try:
        from app.tasks.review_task import run_code_review_task
        run_code_review_task.delay(str(scan.id), sanitized, reasoning_level)
    except Exception:
        # If Celery/Redis is down, mark completed so UI doesn't hang
        scan.status = "completed"
        await session.commit()

    # 6. Evaluate against repository policy (if one exists)
    from app.db.models.policy import Policy
    from app.api.v1.policies import evaluate_findings_against_policy
    policy_stmt = select(Policy).where(Policy.repository == body.repository)
    policy = (await session.execute(policy_stmt)).scalar_one_or_none()

    policy_result = None
    if policy is not None:
        eval_result = evaluate_findings_against_policy(policy, all_findings)
        policy_result = PolicyCheckResult(
            blocked=eval_result.blocked,
            violations_count=len(eval_result.violations),
            max_severity_allowed=eval_result.max_severity_allowed,
        )

    # 7. Build response with suppression annotations
    finding_responses = await _annotate_findings_suppression(session, scan.findings)

    return ScanResponse(
        id=scan.id,
        repository=scan.repository,
        commit_hash=scan.commit_hash,
        status=scan.status,
        risk_score=scan.risk_score,
        reasoning_level=scan.reasoning_level,
        synthesis_json=scan.synthesis_json,
        findings=finding_responses,
        policy_check=policy_result,
        created_at=scan.created_at,
    )


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

    finding_responses = await _annotate_findings_suppression(session, scan.findings)
    return ScanResponse(
        id=scan.id,
        repository=scan.repository,
        commit_hash=scan.commit_hash,
        status=scan.status,
        risk_score=scan.risk_score,
        reasoning_level=scan.reasoning_level,
        synthesis_json=scan.synthesis_json,
        findings=finding_responses,
        created_at=scan.created_at,
    )


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
