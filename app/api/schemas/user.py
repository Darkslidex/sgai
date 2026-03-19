"""Schemas Pydantic para usuarios y preferencias."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserProfileCreate(BaseModel):
    telegram_chat_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=18, le=120)
    weight_kg: float = Field(gt=0, le=500)
    height_cm: float = Field(gt=0, le=300)
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"]
    goal: Literal["maintain", "lose", "gain"]
    max_storage_volume: dict = Field(default_factory=dict)


class UserProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    age: int | None = Field(None, ge=18, le=120)
    weight_kg: float | None = Field(None, gt=0, le=500)
    height_cm: float | None = Field(None, gt=0, le=300)
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"] | None = None
    goal: Literal["maintain", "lose", "gain"] | None = None
    max_storage_volume: dict | None = None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_chat_id: str
    name: str
    age: int
    weight_kg: float
    height_cm: float
    activity_level: str
    goal: str
    max_storage_volume: dict
    created_at: datetime
    updated_at: datetime


class UserPreferenceCreate(BaseModel):
    user_id: int
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=255)


class UserPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    key: str
    value: str
    created_at: datetime
