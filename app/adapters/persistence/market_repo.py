"""Implementación SQLAlchemy del MarketRepositoryPort."""

from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers.market_price_mapper import market_price_to_domain
from app.adapters.persistence.mappers.pantry_item_mapper import pantry_item_to_domain
from app.adapters.persistence.market_price_orm import MarketPriceORM
from app.adapters.persistence.pantry_item_orm import PantryItemORM
from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem
from app.domain.ports.market_repository import MarketRepositoryPort


class MarketRepository(MarketRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_price(self, price: MarketPrice) -> MarketPrice:
        orm = MarketPriceORM(
            ingredient_id=price.ingredient_id,
            price_ars=price.price_ars,
            source=price.source,
            store=price.store,
            confidence=price.confidence,
            date=price.date,
            created_at=datetime.utcnow(),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return market_price_to_domain(orm)

    async def get_current_price(self, ingredient_id: int) -> MarketPrice | None:
        result = await self._session.execute(
            select(MarketPriceORM)
            .where(MarketPriceORM.ingredient_id == ingredient_id)
            .order_by(MarketPriceORM.date.desc())
            .limit(1)
        )
        orm = result.scalar_one_or_none()
        return market_price_to_domain(orm) if orm else None

    async def get_price_history(self, ingredient_id: int, days: int = 30) -> list[MarketPrice]:
        cutoff = date.today() - timedelta(days=days)
        result = await self._session.execute(
            select(MarketPriceORM)
            .where(
                MarketPriceORM.ingredient_id == ingredient_id,
                MarketPriceORM.date >= cutoff,
            )
            .order_by(MarketPriceORM.date.desc())
        )
        return [market_price_to_domain(row) for row in result.scalars()]

    async def get_all_current_prices(self) -> list[MarketPrice]:
        """Precio más reciente por ingrediente."""
        subq = (
            select(
                MarketPriceORM.ingredient_id,
                func.max(MarketPriceORM.date).label("max_date"),
            )
            .group_by(MarketPriceORM.ingredient_id)
            .subquery()
        )
        result = await self._session.execute(
            select(MarketPriceORM).join(
                subq,
                and_(
                    MarketPriceORM.ingredient_id == subq.c.ingredient_id,
                    MarketPriceORM.date == subq.c.max_date,
                ),
            )
        )
        return [market_price_to_domain(row) for row in result.scalars()]

    async def get_pantry(self, user_id: int) -> list[PantryItem]:
        result = await self._session.execute(
            select(PantryItemORM).where(PantryItemORM.user_id == user_id)
        )
        return [pantry_item_to_domain(row) for row in result.scalars()]

    async def update_pantry(self, item: PantryItem) -> PantryItem:
        # Upsert: buscar por user_id + ingredient_id
        result = await self._session.execute(
            select(PantryItemORM).where(
                PantryItemORM.user_id == item.user_id,
                PantryItemORM.ingredient_id == item.ingredient_id,
            )
        )
        existing = result.scalar_one_or_none()
        now = datetime.utcnow()
        if existing:
            existing.quantity_amount = item.quantity_amount
            existing.unit = item.unit
            existing.expires_at = item.expires_at
            existing.updated_at = now
            await self._session.flush()
            await self._session.refresh(existing)
            return pantry_item_to_domain(existing)
        orm = PantryItemORM(
            user_id=item.user_id,
            ingredient_id=item.ingredient_id,
            quantity_amount=item.quantity_amount,
            unit=item.unit,
            expires_at=item.expires_at,
            created_at=now,
            updated_at=now,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return pantry_item_to_domain(orm)
