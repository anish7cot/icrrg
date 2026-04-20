"""EvalRun model — stores evaluation run results with precision/recall/F1."""

import uuid

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin


class EvalRun(TimestampMixin, Base):
    __tablename__ = "eval_runs"

    engine: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "detection", "llm", "all"
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    f1: Mapped[float] = mapped_column(Float, nullable=False)
    tp_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fp_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_scenarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
