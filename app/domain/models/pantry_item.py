"""Modelo de dominio: ítem en la despensa/inventario personal."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PantryItem:
    id: int
    user_id: int
    ingredient_id: int
    quantity_amount: float
    unit: str  # kg, g, litro, ml, unidad
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
