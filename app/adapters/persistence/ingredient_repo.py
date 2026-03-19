"""Implementación SQLAlchemy del IngredientRepositoryPort."""

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.ingredient_orm import IngredientORM
from app.adapters.persistence.mappers.ingredient_mapper import ingredient_to_domain
from app.domain.models.ingredient import Ingredient
from app.domain.ports.ingredient_repository import IngredientRepositoryPort


class IngredientRepository(IngredientRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_ingredient(self, ingredient: Ingredient) -> Ingredient:
        orm = IngredientORM(
            name=ingredient.name,
            aliases=ingredient.aliases,
            category=ingredient.category,
            storage_type=ingredient.storage_type,
            unit=ingredient.unit,
            protein_per_100g=ingredient.protein_per_100g,
            calories_per_100g=ingredient.calories_per_100g,
            avg_shelf_life_days=ingredient.avg_shelf_life_days,
            created_at=datetime.utcnow(),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return ingredient_to_domain(orm)

    async def get_ingredient(self, ingredient_id: int) -> Ingredient | None:
        result = await self._session.execute(
            select(IngredientORM).where(IngredientORM.id == ingredient_id)
        )
        orm = result.scalar_one_or_none()
        return ingredient_to_domain(orm) if orm else None

    async def list_ingredients(self) -> list[Ingredient]:
        result = await self._session.execute(
            select(IngredientORM).order_by(IngredientORM.name)
        )
        return [ingredient_to_domain(row) for row in result.scalars()]

    async def search_ingredients(self, query: str) -> list[Ingredient]:
        pattern = f"%{query.lower()}%"
        result = await self._session.execute(
            select(IngredientORM)
            .where(IngredientORM.name.ilike(pattern))
            .order_by(IngredientORM.name)
        )
        return [ingredient_to_domain(row) for row in result.scalars()]
