"""Mapper: Recipe ↔ RecipeORM."""

from app.adapters.persistence.recipe_orm import RecipeORM
from app.domain.models.recipe import Recipe


def recipe_to_domain(orm: RecipeORM) -> Recipe:
    return Recipe(
        id=orm.id,
        name=orm.name,
        description=orm.description,
        prep_time_minutes=orm.prep_time_minutes,
        is_batch_friendly=orm.is_batch_friendly,
        reheatable_days=orm.reheatable_days,
        servings=orm.servings,
        calories_per_serving=orm.calories_per_serving,
        protein_per_serving=orm.protein_per_serving,
        carbs_per_serving=orm.carbs_per_serving,
        fat_per_serving=orm.fat_per_serving,
        instructions=orm.instructions,
        tags=orm.tags or [],
        created_at=orm.created_at,
    )


def recipe_to_orm(domain: Recipe) -> RecipeORM:
    return RecipeORM(
        id=domain.id,
        name=domain.name,
        description=domain.description,
        prep_time_minutes=domain.prep_time_minutes,
        is_batch_friendly=domain.is_batch_friendly,
        reheatable_days=domain.reheatable_days,
        servings=domain.servings,
        calories_per_serving=domain.calories_per_serving,
        protein_per_serving=domain.protein_per_serving,
        carbs_per_serving=domain.carbs_per_serving,
        fat_per_serving=domain.fat_per_serving,
        instructions=domain.instructions,
        tags=domain.tags,
        created_at=domain.created_at,
    )
