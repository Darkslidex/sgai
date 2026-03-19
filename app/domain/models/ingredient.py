"""Modelo de dominio: ingrediente."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Ingredient:
    id: int
    name: str
    aliases: list[str]  # Nombres alternativos argentinos
    category: str  # proteina, carbohidrato, grasa, vegetal, lacteo, condimento
    storage_type: str  # refrigerado, seco, congelado
    unit: str  # kg, litro, unidad
    protein_per_100g: float | None
    calories_per_100g: float | None
    avg_shelf_life_days: int | None
    created_at: datetime
