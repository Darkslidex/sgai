"""Modelo ORM: weekly_plans."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeeklyPlanORM(Base):
    __tablename__ = "weekly_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    shopping_list_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_cost_ars: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
