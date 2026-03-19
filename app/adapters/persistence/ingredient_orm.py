"""Modelo ORM: ingredients."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IngredientORM(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_type: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    protein_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
