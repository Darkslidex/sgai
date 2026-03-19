"""Schemas Pydantic para registros de salud."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthLogCreate(BaseModel):
    user_id: int
    date: date
    sleep_score: float | None = Field(None, ge=0, le=100)
    stress_level: float | None = Field(None, ge=0, le=10)
    hrv: float | None = Field(None, ge=0)
    steps: int | None = Field(None, ge=0)
    mood: Literal["great", "good", "neutral", "bad", "terrible"] | None = None
    notes: str | None = None
    source: Literal["manual", "health_connect"] = "manual"


class HealthLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: date
    sleep_score: float | None
    stress_level: float | None
    hrv: float | None
    steps: int | None
    mood: str | None
    notes: str | None
    source: str
    created_at: datetime


class WeeklyAvgResponse(BaseModel):
    avg_sleep_score: float | None
    avg_stress_level: float | None
    avg_hrv: float | None
    avg_steps: float | None
    week_start: str
    week_end: str
