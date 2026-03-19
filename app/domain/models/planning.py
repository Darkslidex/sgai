"""Modelo de dominio: plan semanal de alimentación."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class WeeklyPlan:
    id: int
    user_id: int
    week_start: date
    plan_json: dict  # Estructura completa del plan generado por IA
    shopping_list_json: dict  # Lista de compras con precios
    total_cost_ars: float
    is_active: bool
    created_at: datetime
    expires_at: datetime  # Caché de 7 días
