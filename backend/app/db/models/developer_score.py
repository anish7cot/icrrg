"""DeveloperScore model — weekly scoring for developer leaderboard."""

import uuid
from datetime import date

from sqlalchemy import Date, Float, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin


class DeveloperScore(TimestampMixin, Base):
    __tablename__ = "developer_scores"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uq_user_period"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Raw counts
    total_scans: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clean_scan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clean_scan_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    critical_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Derived metrics
    findings_per_scan: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weighted_finding_density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feedback_given_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    improvement_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Sub-scores (0-100)
    security_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    responsiveness_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    improvement_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)

    # Ranking
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user = relationship("User", backref="scores")
