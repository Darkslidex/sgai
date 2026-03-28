"""Validador Pydantic para output del LLM — evita que datos alucinados lleguen a la DB.

Si el LLM genera un plan con calorías irreales, ingredientes duplicados o datos
fuera de rangos biológicamente posibles, este validador lo rechaza ANTES de persistir.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class ValidatedMeal(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    calories: int | None = Field(default=None, ge=50, le=3000)
    protein_g: float | None = Field(default=None, ge=0, le=200)
    carbs_g: float | None = Field(default=None, ge=0, le=500)
    fat_g: float | None = Field(default=None, ge=0, le=200)
    prep_time_min: int | None = Field(default=None, ge=1, le=480)

    @field_validator("name")
    @classmethod
    def name_not_placeholder(cls, v: str) -> str:
        forbidden = ["placeholder", "test", "ejemplo", "lorem", "undefined", "null"]
        if any(f in v.lower() for f in forbidden):
            raise ValueError(f"Nombre de comida inválido (parece placeholder): '{v}'")
        return v


class ValidatedIngredient(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    quantity: float = Field(gt=0, le=10000)
    unit: str = Field(min_length=1, max_length=20)
    estimated_cost_ars: Optional[float] = Field(default=None, ge=0, le=1_000_000)

    @field_validator("unit")
    @classmethod
    def valid_unit(cls, v: str) -> str:
        allowed = {"g", "kg", "ml", "l", "lt", "unidad", "unidades", "taza", "cdas", "cda"}
        if v.lower() not in allowed:
            raise ValueError(f"Unidad inválida: '{v}'. Permitidas: {allowed}")
        return v.lower()


class ValidatedDayPlan(BaseModel):
    day: str = Field(min_length=1, max_length=20)
    lunch: str = Field(min_length=3, max_length=200)
    dinner: str = Field(min_length=3, max_length=200)

    @field_validator("lunch", "dinner")
    @classmethod
    def not_empty_meal(cls, v: str) -> str:
        forbidden = ["placeholder", "sin comida", "no definido", "undefined"]
        if any(f in v.lower() for f in forbidden):
            raise ValueError(f"Comida inválida (parece placeholder): '{v}'")
        return v


class ValidatedWeeklyPlan(BaseModel):
    days: List[ValidatedDayPlan] = Field(min_length=1, max_length=7)
    shopping_list: List[ValidatedIngredient]
    total_cost_ars: Optional[float] = Field(default=None, ge=0, le=2_000_000)
    cooking_day: str = Field(min_length=1, max_length=20)
    prep_steps: List[str] = Field(default_factory=list)

    @field_validator("shopping_list")
    @classmethod
    def no_duplicate_ingredients(cls, v: List[ValidatedIngredient]) -> List[ValidatedIngredient]:
        names = [i.name.lower().strip() for i in v]
        if len(names) != len(set(names)):
            dupes = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Lista de compras tiene ingredientes duplicados: {set(dupes)}")
        return v

    @field_validator("total_cost_ars")
    @classmethod
    def realistic_cost(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 100:
            raise ValueError(f"Costo total irreal para Argentina: ARS {v}")
        return v


def validate_weekly_plan(raw_json: dict) -> ValidatedWeeklyPlan:
    """Valida un plan semanal generado por el LLM.

    Raises ValueError si el plan no pasa validación.
    Retorna ValidatedWeeklyPlan si es válido.
    """
    return ValidatedWeeklyPlan.model_validate(raw_json)
