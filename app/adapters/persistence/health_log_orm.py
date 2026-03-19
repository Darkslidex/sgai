"""Modelo ORM: health_logs."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HealthLogORM(Base):
    __tablename__ = "health_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sleep_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    stress_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    hrv: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
