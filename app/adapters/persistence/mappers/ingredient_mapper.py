"""Mapper: Ingredient ↔ IngredientORM."""

from app.adapters.persistence.ingredient_orm import IngredientORM
from app.domain.models.ingredient import Ingredient


def ingredient_to_domain(orm: IngredientORM) -> Ingredient:
    return Ingredient(
        id=orm.id,
        name=orm.name,
        aliases=orm.aliases or [],
        category=orm.category,
        storage_type=orm.storage_type,
        unit=orm.unit,
        protein_per_100g=orm.protein_per_100g,
        calories_per_100g=orm.calories_per_100g,
        avg_shelf_life_days=orm.avg_shelf_life_days,
        created_at=orm.created_at,
    )


def ingredient_to_orm(domain: Ingredient) -> IngredientORM:
    return IngredientORM(
        id=domain.id,
        name=domain.name,
        aliases=domain.aliases,
        category=domain.category,
        storage_type=domain.storage_type,
        unit=domain.unit,
        protein_per_100g=domain.protein_per_100g,
        calories_per_100g=domain.calories_per_100g,
        avg_shelf_life_days=domain.avg_shelf_life_days,
        created_at=domain.created_at,
    )
