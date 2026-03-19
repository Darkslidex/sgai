"""Modelo de dominio: preferencia/restricción del usuario (key-value)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserPreference:
    id: int
    user_id: int
    key: str  # ej: "sin_gluten", "vegetariano", "alergia_mani"
    value: str  # ej: "true", "moderado", "severa"
    created_at: datetime
