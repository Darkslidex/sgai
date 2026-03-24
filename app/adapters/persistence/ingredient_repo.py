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

    async def search_ingredients_fuzzy(
        self, query: str, threshold: float = 0.3, limit: int = 5
    ) -> list[Ingredient]:
        """Búsqueda fuzzy por nombre usando pg_trgm similarity.

        Requiere extensión pg_trgm en PostgreSQL (migración 002).
        Cae automáticamente a ILIKE si pg_trgm no está disponible (ej. SQLite en tests).
        """
        from sqlalchemy import text

        try:
            result = await self._session.execute(
                text(
                    "SELECT * FROM ingredients "
                    "WHERE similarity(LOWER(name), LOWER(:query)) > :threshold "
                    "ORDER BY similarity(LOWER(name), LOWER(:query)) DESC "
                    "LIMIT :limit"
                ),
                {"query": query, "threshold": threshold, "limit": limit},
            )
            rows = result.mappings().all()
            if rows:
                return [
                    ingredient_to_domain(
                        IngredientORM(**{k: v for k, v in row.items()})
                    )
                    for row in rows
                ]
        except Exception:
            pass  # pg_trgm no disponible (SQLite en tests) → fallback

        return await self.search_ingredients(query)
