"""Mapper: MarketPrice ↔ MarketPriceORM."""

from app.adapters.persistence.market_price_orm import MarketPriceORM
from app.domain.models.market import MarketPrice


def market_price_to_domain(orm: MarketPriceORM) -> MarketPrice:
    return MarketPrice(
        id=orm.id,
        ingredient_id=orm.ingredient_id,
        price_ars=orm.price_ars,
        source=orm.source,
        store=orm.store,
        confidence=orm.confidence,
        date=orm.date,
        created_at=orm.created_at,
    )


def market_price_to_orm(domain: MarketPrice) -> MarketPriceORM:
    return MarketPriceORM(
        id=domain.id,
        ingredient_id=domain.ingredient_id,
        price_ars=domain.price_ars,
        source=domain.source,
        store=domain.store,
        confidence=domain.confidence,
        date=domain.date,
        created_at=domain.created_at,
    )
