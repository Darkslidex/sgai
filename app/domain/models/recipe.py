"""Modelo de dominio: receta."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Recipe:
    id: int
    name: str
    description: str
    prep_time_minutes: int
    is_batch_friendly: bool  # Apta para batch cooking 1x5
    reheatable_days: int  # Estabilidad al recalentar (max 5)
    servings: int
    calories_per_serving: float
    protein_per_serving: float
    carbs_per_serving: float
    fat_per_serving: float
    instructions: str  # JSON serializado con pasos
    tags: list[str]  # ej: ["alta_proteina", "rapida", "baja_energia"]
    created_at: datetime
