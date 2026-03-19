"""Modelo de dominio: registro de salud diario."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class HealthLog:
    id: int
    user_id: int
    date: date
    sleep_score: float | None  # 0-100
    stress_level: float | None  # 0-10
    hrv: float | None  # Heart Rate Variability en ms
    steps: int | None
    mood: str | None  # great, good, neutral, bad, terrible
    notes: str | None
    source: str  # manual, health_connect
    created_at: datetime
