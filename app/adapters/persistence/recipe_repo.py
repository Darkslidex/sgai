"""Implementación SQLAlchemy del RecipeRepositoryPort."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers.recipe_ingredient_mapper import recipe_ingredient_to_domain
from app.adapters.persistence.mappers.recipe_mapper import recipe_to_domain
from app.adapters.persistence.recipe_ingredient_orm import RecipeIngredientORM
from app.adapters.persistence.recipe_orm import RecipeORM
from app.domain.models.recipe import Recipe
from app.domain.models.recipe_ingredient import RecipeIngredient
from app.domain.ports.recipe_repository import RecipeRepositoryPort


class RecipeRepository(RecipeRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_recipe(self, recipe: Recipe, ingredients: list[RecipeIngredient]) -> Recipe:
        recipe_orm = RecipeORM(
            name=recipe.name,
            description=recipe.description,
            prep_time_minutes=recipe.prep_time_minutes,
            is_batch_friendly=recipe.is_batch_friendly,
            reheatable_days=recipe.reheatable_days,
            servings=recipe.servings,
            calories_per_serving=recipe.calories_per_serving,
            protein_per_serving=recipe.protein_per_serving,
            carbs_per_serving=recipe.carbs_per_serving,
            fat_per_serving=recipe.fat_per_serving,
            instructions=recipe.instructions,
            tags=recipe.tags,
            created_at=datetime.utcnow(),
        )
        self._session.add(recipe_orm)
        await self._session.flush()  # obtener recipe_orm.id

        for ing in ingredients:
            ri_orm = RecipeIngredientORM(
                recipe_id=recipe_orm.id,
                ingredient_id=ing.ingredient_id,
                quantity_amount=ing.quantity_amount,
                unit=ing.unit,
            )
            self._session.add(ri_orm)

        await self._session.flush()
        await self._session.refresh(recipe_orm)
        return recipe_to_domain(recipe_orm)

    async def get_recipe(self, recipe_id: int) -> Recipe | None:
        result = await self._session.execute(
            select(RecipeORM).where(RecipeORM.id == recipe_id)
        )
        orm = result.scalar_one_or_none()
        return recipe_to_domain(orm) if orm else None

    async def list_recipes(self, filters: dict | None = None) -> list[Recipe]:
        stmt = select(RecipeORM)
        if filters:
            if "is_batch_friendly" in filters:
                stmt = stmt.where(RecipeORM.is_batch_friendly == filters["is_batch_friendly"])
            if "max_prep_time" in filters:
                stmt = stmt.where(RecipeORM.prep_time_minutes <= filters["max_prep_time"])
            if "min_reheatable_days" in filters:
                stmt = stmt.where(RecipeORM.reheatable_days >= filters["min_reheatable_days"])
        result = await self._session.execute(stmt.order_by(RecipeORM.name))
        return [recipe_to_domain(row) for row in result.scalars()]

    async def get_overlapping_recipes(
        self, ingredient_ids: list[int], min_overlap: int = 2
    ) -> list[Recipe]:
        """Recetas que comparten al menos min_overlap ingredientes con la lista dada."""
        subq = (
            select(
                RecipeIngredientORM.recipe_id,
                func.count(RecipeIngredientORM.ingredient_id).label("overlap_count"),
            )
            .where(RecipeIngredientORM.ingredient_id.in_(ingredient_ids))
            .group_by(RecipeIngredientORM.recipe_id)
            .having(func.count(RecipeIngredientORM.ingredient_id) >= min_overlap)
            .subquery()
        )
        result = await self._session.execute(
            select(RecipeORM).join(subq, RecipeORM.id == subq.c.recipe_id)
        )
        return [recipe_to_domain(row) for row in result.scalars()]

    async def get_recipe_ingredients(self, recipe_id: int) -> list[RecipeIngredient]:
        result = await self._session.execute(
            select(RecipeIngredientORM).where(RecipeIngredientORM.recipe_id == recipe_id)
        )
        return [recipe_ingredient_to_domain(row) for row in result.scalars()]
