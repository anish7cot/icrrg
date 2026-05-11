from sqlalchemy import Integer, String, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin


class Scan(TimestampMixin, Base):
    __tablename__ = "scans"

    repository: Mapped[str] = mapped_column(String(500), nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    diff_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reasoning_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    synthesis_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    findings = relationship("ScanFinding", back_populates="scan", cascade="all, delete-orphan")
