"""Mapper: RecipeIngredient ↔ RecipeIngredientORM."""

from app.adapters.persistence.recipe_ingredient_orm import RecipeIngredientORM
from app.domain.models.recipe_ingredient import RecipeIngredient


def recipe_ingredient_to_domain(orm: RecipeIngredientORM) -> RecipeIngredient:
    return RecipeIngredient(
        id=orm.id,
        recipe_id=orm.recipe_id,
        ingredient_id=orm.ingredient_id,
        quantity_amount=orm.quantity_amount,
        unit=orm.unit,
    )


def recipe_ingredient_to_orm(domain: RecipeIngredient) -> RecipeIngredientORM:
    return RecipeIngredientORM(
        id=domain.id,
        recipe_id=domain.recipe_id,
        ingredient_id=domain.ingredient_id,
        quantity_amount=domain.quantity_amount,
        unit=domain.unit,
    )
