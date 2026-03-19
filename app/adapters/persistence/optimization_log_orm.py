"""Modelo ORM: optimization_logs (feedback loop de IA)."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OptimizationLogORM(Base):
    __tablename__ = "optimization_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    optimization_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
