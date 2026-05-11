"""Periodic job to calculate developer scores for a rolling 7-day window.

Can be triggered:
1. Via admin API: POST /api/v1/scoreboard/calculate
2. Via Celery beat schedule (weekly)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.developer_score import DeveloperScore
from app.db.models.finding_feedback import FindingFeedback
from app.db.models.scan import Scan
from app.db.models.scan_finding import ScanFinding
from app.db.models.user import User
from app.db.models.user_project import UserProject
from app.scoring.calculator import compute_full_score

logger = logging.getLogger(__name__)


async def calculate_scores_for_period(
    session: AsyncSession,
    period_end: date | None = None,
    period_days: int = 7,
) -> int:
    """Calculate scores for all active developers for a given period.

    Args:
        session: Async DB session
        period_end: End date of the scoring window (inclusive). Defaults to today.
        period_days: Length of scoring window in days. Default 7 (weekly).

    Returns:
        Number of scores computed.
    """
    if period_end is None:
        period_end = date.today()
    period_start = period_end - timedelta(days=period_days - 1)
    prev_period_start = period_start - timedelta(days=period_days)
    prev_period_end = period_start - timedelta(days=1)

    # Get all active users with developer role
    users_result = await session.execute(
        select(User).where(User.is_active == True, User.role == "developer")  # noqa: E712
    )
    users = users_result.scalars().all()

    scores_computed = 0

    for user in users:
        # Get user's repositories
        repos_result = await session.execute(
            select(UserProject.repository).where(UserProject.user_id == user.id)
        )
        user_repos = [r[0] for r in repos_result.all()]
        if not user_repos:
            continue

        # Current period metrics
        metrics = await _get_period_metrics(session, user.id, user_repos, period_start, period_end)
        if metrics["total_scans"] == 0:
            continue

        # Previous period density for improvement score
        prev_metrics = await _get_period_metrics(session, user.id, user_repos, prev_period_start, prev_period_end)
        previous_density = None
        if prev_metrics["total_scans"] > 0:
            from app.scoring.calculator import calculate_weighted_density
            previous_density = calculate_weighted_density(
                prev_metrics["critical"], prev_metrics["high"],
                prev_metrics["medium"], prev_metrics["low"],
                prev_metrics["total_scans"],
            )

        # Compute score
        breakdown = compute_full_score(
            total_scans=metrics["total_scans"],
            total_findings=metrics["total_findings"],
            clean_scan_count=metrics["clean_scan_count"],
            critical_findings=metrics["critical"],
            high_findings=metrics["high"],
            medium_findings=metrics["medium"],
            low_findings=metrics["low"],
            feedback_given_count=metrics["feedback_count"],
            total_findings_in_scans=metrics["total_findings"],
            previous_density=previous_density,
        )

        # Upsert score record
        existing = await session.execute(
            select(DeveloperScore).where(
                DeveloperScore.user_id == user.id,
                DeveloperScore.period_start == period_start,
            )
        )
        score_record = existing.scalar_one_or_none()

        if score_record is None:
            score_record = DeveloperScore(user_id=user.id, period_start=period_start, period_end=period_end)
            session.add(score_record)

        # Update all fields
        score_record.period_end = period_end
        score_record.total_scans = breakdown.total_scans
        score_record.total_findings = breakdown.total_findings
        score_record.clean_scan_count = breakdown.clean_scan_count
        score_record.clean_scan_rate = breakdown.clean_scan_rate
        score_record.critical_findings = breakdown.critical_findings
        score_record.high_findings = breakdown.high_findings
        score_record.medium_findings = breakdown.medium_findings
        score_record.low_findings = breakdown.low_findings
        score_record.findings_per_scan = breakdown.findings_per_scan
        score_record.weighted_finding_density = breakdown.weighted_finding_density
        score_record.feedback_given_count = breakdown.feedback_given_count
        score_record.feedback_rate = breakdown.feedback_rate
        score_record.improvement_rate = breakdown.improvement_rate
        score_record.security_score = breakdown.security_score
        score_record.responsiveness_score = breakdown.responsiveness_score
        score_record.improvement_score = breakdown.improvement_score
        score_record.composite_score = breakdown.composite_score

        scores_computed += 1

    # Compute rankings for this period
    await _compute_rankings(session, period_start)
    await session.commit()

    logger.info("Computed %d developer scores for period %s to %s", scores_computed, period_start, period_end)
    return scores_computed


async def _get_period_metrics(
    session: AsyncSession,
    user_id,
    user_repos: list[str],
    start: date,
    end: date,
) -> dict:
    """Get scan metrics for a user in a date range."""
    # Get scans in period for user's repos
    scans_stmt = (
        select(Scan)
        .where(
            Scan.repository.in_(user_repos),
            func.date(Scan.created_at) >= start,
            func.date(Scan.created_at) <= end,
            Scan.status == "completed",
        )
    )
    scans_result = await session.execute(scans_stmt)
    scans = scans_result.scalars().all()

    total_scans = len(scans)
    if total_scans == 0:
        return {
            "total_scans": 0, "total_findings": 0, "clean_scan_count": 0,
            "critical": 0, "high": 0, "medium": 0, "low": 0, "feedback_count": 0,
        }

    scan_ids = [s.id for s in scans]

    # Count findings by severity
    findings_stmt = (
        select(ScanFinding.severity, func.count(ScanFinding.id))
        .where(ScanFinding.scan_id.in_(scan_ids))
        .group_by(ScanFinding.severity)
    )
    findings_result = await session.execute(findings_stmt)
    severity_counts = {row[0]: row[1] for row in findings_result.all()}

    total_findings = sum(severity_counts.values())
    clean_scan_count = sum(1 for s in scans if s.risk_score == 0 or s.risk_score is None)

    # Count feedback given by user
    feedback_stmt = (
        select(func.count(FindingFeedback.id))
        .join(ScanFinding, FindingFeedback.scan_finding_id == ScanFinding.id)
        .where(
            FindingFeedback.user_id == user_id,
            ScanFinding.scan_id.in_(scan_ids),
        )
    )
    feedback_result = await session.execute(feedback_stmt)
    feedback_count = feedback_result.scalar() or 0

    return {
        "total_scans": total_scans,
        "total_findings": total_findings,
        "clean_scan_count": clean_scan_count,
        "critical": severity_counts.get("critical", 0),
        "high": severity_counts.get("high", 0),
        "medium": severity_counts.get("medium", 0),
        "low": severity_counts.get("low", 0),
        "feedback_count": feedback_count,
    }


async def _compute_rankings(session: AsyncSession, period_start: date) -> None:
    """Rank all scores for a period by composite_score descending."""
    scores_result = await session.execute(
        select(DeveloperScore)
        .where(DeveloperScore.period_start == period_start)
        .order_by(DeveloperScore.composite_score.desc(), DeveloperScore.critical_findings.asc())
    )
    scores = scores_result.scalars().all()

    for rank, score in enumerate(scores, start=1):
        score.rank = rank
