"""Schemas Pydantic para recetas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecipeIngredientCreate(BaseModel):
    ingredient_id: int
    quantity_amount: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=20)


class RecipeIngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_id: int
    ingredient_id: int
    quantity_amount: float
    unit: str


class RecipeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    prep_time_minutes: int = Field(ge=1, le=600)
    is_batch_friendly: bool = False
    reheatable_days: int = Field(ge=1, le=5)
    servings: int = Field(ge=1, le=50)
    calories_per_serving: float = Field(gt=0)
    protein_per_serving: float = Field(ge=0)
    carbs_per_serving: float = Field(ge=0)
    fat_per_serving: float = Field(ge=0)
    instructions: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    ingredients: list[RecipeIngredientCreate] = Field(default_factory=list)


class RecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    prep_time_minutes: int
    is_batch_friendly: bool
    reheatable_days: int
    servings: int
    calories_per_serving: float
    protein_per_serving: float
    carbs_per_serving: float
    fat_per_serving: float
    instructions: str
    tags: list[str]
    created_at: datetime
