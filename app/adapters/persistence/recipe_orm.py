"""Modelo ORM: recipes."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecipeORM(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    prep_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_batch_friendly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reheatable_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    servings: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_per_serving: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_serving: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_per_serving: Mapped[float] = mapped_column(Float, nullable=False)
    fat_per_serving: Mapped[float] = mapped_column(Float, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
