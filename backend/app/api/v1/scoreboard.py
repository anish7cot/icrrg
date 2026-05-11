"""Developer Scoreboard API endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_manager_or_admin
from app.db.models.developer_score import DeveloperScore
from app.db.models.user import User
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/scoreboard", tags=["scoreboard"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    composite_score: float
    security_score: float
    responsiveness_score: float
    improvement_score: float
    total_scans: int
    clean_scan_rate: float
    findings_per_scan: float
    period_start: date
    period_end: date

    model_config = {"from_attributes": True}


class MyScoreResponse(BaseModel):
    composite_score: float
    security_score: float
    responsiveness_score: float
    improvement_score: float
    total_scans: int
    total_findings: int
    clean_scan_rate: float
    findings_per_scan: float
    feedback_rate: float
    improvement_rate: float
    rank: int
    percentile: float  # Top X% (lower = better)
    period_start: date
    period_end: date


class ScoreHistoryEntry(BaseModel):
    period_start: date
    composite_score: float
    security_score: float
    responsiveness_score: float
    improvement_score: float


class MethodologyResponse(BaseModel):
    version: str = "1.0"
    description: str
    weights: dict[str, float]
    sub_scores: list[dict]
    scientific_basis: list[dict]


# ---------------------------------------------------------------------------
# GET /api/v1/scoreboard — Full leaderboard (admin/manager only)
# ---------------------------------------------------------------------------
@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    period_start: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session),
):
    """Full leaderboard — requires admin or manager role."""
    if period_start is None:
        # Get latest period
        latest = await session.execute(
            select(func.max(DeveloperScore.period_start))
        )
        period_start = latest.scalar()
        if period_start is None:
            return []

    stmt = (
        select(DeveloperScore, User.username)
        .join(User, DeveloperScore.user_id == User.id)
        .where(DeveloperScore.period_start == period_start)
        .order_by(DeveloperScore.rank.asc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        LeaderboardEntry(
            rank=score.rank,
            username=username,
            composite_score=score.composite_score,
            security_score=score.security_score,
            responsiveness_score=score.responsiveness_score,
            improvement_score=score.improvement_score,
            total_scans=score.total_scans,
            clean_scan_rate=score.clean_scan_rate,
            findings_per_scan=score.findings_per_scan,
            period_start=score.period_start,
            period_end=score.period_end,
        )
        for score, username in rows
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/scoreboard/me — Own score + percentile
# ---------------------------------------------------------------------------
@router.get("/me", response_model=MyScoreResponse | None)
async def get_my_score(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current user's latest score and anonymized percentile."""
    # Get latest period
    latest = await session.execute(
        select(func.max(DeveloperScore.period_start))
    )
    period_start = latest.scalar()
    if period_start is None:
        return None

    # Get user's score
    stmt = select(DeveloperScore).where(
        DeveloperScore.user_id == user.id,
        DeveloperScore.period_start == period_start,
    )
    result = await session.execute(stmt)
    my_score = result.scalar_one_or_none()
    if my_score is None:
        return None

    # Calculate percentile
    total_count = await session.execute(
        select(func.count(DeveloperScore.id)).where(DeveloperScore.period_start == period_start)
    )
    total = total_count.scalar() or 1
    percentile = round((my_score.rank / total) * 100, 1)

    return MyScoreResponse(
        composite_score=my_score.composite_score,
        security_score=my_score.security_score,
        responsiveness_score=my_score.responsiveness_score,
        improvement_score=my_score.improvement_score,
        total_scans=my_score.total_scans,
        total_findings=my_score.total_findings,
        clean_scan_rate=my_score.clean_scan_rate,
        findings_per_scan=my_score.findings_per_scan,
        feedback_rate=my_score.feedback_rate,
        improvement_rate=my_score.improvement_rate,
        rank=my_score.rank,
        percentile=percentile,
        period_start=my_score.period_start,
        period_end=my_score.period_end,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/scoreboard/history — Score trend (last 8 weeks)
# ---------------------------------------------------------------------------
@router.get("/history", response_model=list[ScoreHistoryEntry])
async def get_score_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current user's score history (last 8 periods)."""
    stmt = (
        select(DeveloperScore)
        .where(DeveloperScore.user_id == user.id)
        .order_by(DeveloperScore.period_start.desc())
        .limit(8)
    )
    result = await session.execute(stmt)
    scores = result.scalars().all()

    return [
        ScoreHistoryEntry(
            period_start=s.period_start,
            composite_score=s.composite_score,
            security_score=s.security_score,
            responsiveness_score=s.responsiveness_score,
            improvement_score=s.improvement_score,
        )
        for s in reversed(scores)  # Oldest first for charts
    ]


# ---------------------------------------------------------------------------
# POST /api/v1/scoreboard/calculate — Admin trigger
# ---------------------------------------------------------------------------
@router.post("/calculate")
async def trigger_calculation(
    user: User = Depends(require_manager_or_admin),
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger score calculation for current period (admin only)."""
    from app.scoring.job import calculate_scores_for_period
    count = await calculate_scores_for_period(session)
    return {"status": "completed", "scores_computed": count}


# ---------------------------------------------------------------------------
# POST /api/v1/scoreboard/calculate-mine — Any user trigger (own score only)
# ---------------------------------------------------------------------------
@router.post("/calculate-mine")
async def trigger_my_calculation(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Recalculate the current user's score for the current period."""
    from app.scoring.job import calculate_scores_for_period
    count = await calculate_scores_for_period(session)
    return {"status": "completed", "scores_computed": count}


# ---------------------------------------------------------------------------
# GET /api/v1/scoreboard/methodology — Scoring documentation
# ---------------------------------------------------------------------------
@router.get("/methodology", response_model=MethodologyResponse)
async def get_methodology():
    """Returns the scoring methodology documentation."""
    return MethodologyResponse(
        description=(
            "Developer security scores are computed weekly using a composite of three "
            "sub-scores, each measuring a different dimension of security practice."
        ),
        weights={
            "security": 0.40,
            "responsiveness": 0.30,
            "improvement": 0.30,
        },
        sub_scores=[
            {
                "name": "Security Score",
                "weight": "40%",
                "formula": "clean_scan_rate × 100 - severity_penalties",
                "description": "Measures code hygiene — percentage of scans with zero findings, penalized by critical/high findings.",
                "range": "0-100 (higher = cleaner code)",
            },
            {
                "name": "Responsiveness Score",
                "weight": "30%",
                "formula": "feedback_rate × 100 + bonus(>80%)",
                "description": "Measures engagement — how actively developer triages and provides feedback on findings.",
                "range": "0-100 (higher = more engaged)",
            },
            {
                "name": "Improvement Score",
                "weight": "30%",
                "formula": "50 + (prev_density - curr_density) / prev_density × 50",
                "description": "Measures trend — whether finding density is improving vs prior period.",
                "range": "0-100 (50=neutral, 100=eliminated all findings, 0=doubled)",
            },
        ],
        scientific_basis=[
            {
                "metric": "Security Score",
                "standard": "CWE Density (MITRE)",
                "reference": "CWE findings per unit of code, adapted as findings-per-scan",
            },
            {
                "metric": "Responsiveness Score",
                "standard": "OWASP SAMM - Defect Tracking",
                "reference": "Maturity level based on active triage rate of security findings",
            },
            {
                "metric": "Improvement Score",
                "standard": "Statistical Process Control (SPC)",
                "reference": "Trend analysis comparing current performance against historical baseline",
            },
            {
                "metric": "Cost Savings",
                "standard": "NIST SP 800-65 / IBM SSI",
                "reference": "Pre-commit fix = 1x baseline, production fix = 30x for critical findings",
            },
        ],
    )
