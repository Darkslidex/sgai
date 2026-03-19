"""Modelo de dominio: perfil del usuario."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserProfile:
    id: int
    telegram_chat_id: str
    name: str
    age: int  # Perfil nutricional
    weight_kg: float
    height_cm: float
    activity_level: str  # sedentary, light, moderate, active, very_active
    goal: str  # maintain, lose, gain
    max_storage_volume: dict  # ADR-008: Límite de Capacidad Física por categoría (litros)
    # Ejemplo: {"refrigerados": 50, "secos": 30, "congelados": 20}
    created_at: datetime
    updated_at: datetime
