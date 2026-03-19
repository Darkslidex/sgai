"""Modelo de dominio: relación M:M entre receta e ingrediente."""

from dataclasses import dataclass


@dataclass
class RecipeIngredient:
    id: int
    recipe_id: int
    ingredient_id: int
    quantity_amount: float
    unit: str  # kg, g, litro, ml, unidad
