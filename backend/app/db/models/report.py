from sqlalchemy import String, Date, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin

import datetime


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    repository: Mapped[str] = mapped_column(String(500), nullable=False)
    date_range_start: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    date_range_end: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    audience_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
