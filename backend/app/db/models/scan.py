from sqlalchemy import String, Float
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

    findings = relationship("ScanFinding", back_populates="scan", cascade="all, delete-orphan")
