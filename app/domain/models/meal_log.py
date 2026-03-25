"""Modelo de dominio: registro de consumo alimentario."""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class MealItem:
    """Ítem individual dentro de un registro de comida."""

    ingredient: str
    quantity_g: float
    calories_kcal: float
    protein_g: float | None = None


@dataclass
class MealLog:
    """Registro de una comida consumida por el usuario."""

    id: int
    user_id: int
    date: date
    meal_type: str          # 'desayuno', 'almuerzo', 'cena', 'snack'
    raw_description: str    # Texto literal del usuario
    items: list[MealItem]   # Ítems parseados por el LLM
    total_calories_kcal: float
    total_protein_g: float | None
    source: str             # 'text', 'photo', 'voice'
    notes: str | None
    created_at: datetime
