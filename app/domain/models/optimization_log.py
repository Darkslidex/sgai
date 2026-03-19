"""Modelo de dominio: log de optimización / feedback loop de IA."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class OptimizationLog:
    id: int
    user_id: int
    week_start: date
    feedback: str  # Texto libre del usuario
    optimization_data: dict  # Datos usados/generados por el optimizador
    created_at: datetime
