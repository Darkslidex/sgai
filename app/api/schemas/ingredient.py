"""Schemas Pydantic para ingredientes."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list)
    category: Literal["proteina", "carbohidrato", "grasa", "vegetal", "lacteo", "condimento"]
    storage_type: Literal["refrigerado", "seco", "congelado"]
    unit: Literal["kg", "g", "litro", "ml", "unidad"]
    protein_per_100g: float | None = Field(None, ge=0)
    calories_per_100g: float | None = Field(None, ge=0)
    avg_shelf_life_days: int | None = Field(None, ge=1)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip().lower()


class IngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    aliases: list[str]
    category: str
    storage_type: str
    unit: str
    protein_per_100g: float | None
    calories_per_100g: float | None
    avg_shelf_life_days: int | None
    created_at: datetime
