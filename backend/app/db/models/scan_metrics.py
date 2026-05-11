"""ScanMetrics model — tracks timing, cost, and resource usage per scan."""

import uuid

from sqlalchemy import Boolean, Float, Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin


class ScanMetrics(TimestampMixin, Base):
    __tablename__ = "scan_metrics"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    total_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    regex_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entropy_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ner_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    llm_calls_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reasoning_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    findings_before_dedup: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_after_dedup: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_savings_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    scan = relationship("Scan", backref="metrics", uselist=False)
