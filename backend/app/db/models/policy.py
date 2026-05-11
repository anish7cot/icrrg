"""Policy model — server-side scan policy enforcement per repository."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin


class Policy(TimestampMixin, Base):
    __tablename__ = "policies"

    repository: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True, index=True
    )
    max_severity_allowed: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )  # "critical" | "high" | "medium" | "low" — findings above this block
    required_engines: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # e.g. {"regex": true, "entropy": true, "ner": true, "sca": true}
    sla_overrides: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # e.g. {"critical": 12, "high": 48} — hours
    block_on_sla_breach: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    min_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )  # Only findings >= this confidence trigger policy
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    creator = relationship("User", foreign_keys=[created_by])
