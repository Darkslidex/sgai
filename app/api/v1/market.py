"""Endpoints CRUD para precios de mercado y despensa."""

from datetime import datetime
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.ingredient_repo import IngredientRepository
from app.adapters.persistence.market_repo import MarketRepository
from app.api.schemas.market import (
    CheapestPriceResponse,
    MarketPriceCreate,
    MarketPriceResponse,
    PantryItemCreate,
    PantryItemResponse,
    PriceHistoryStats,
    StorePrice,
)
from app.database import get_db
from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem

router = APIRouter(prefix="/market", tags=["market"])


def get_market_repo(db: AsyncSession = Depends(get_db)) -> MarketRepository:
    return MarketRepository(db)


def get_ingredient_repo(db: AsyncSession = Depends(get_db)) -> IngredientRepository:
    return IngredientRepository(db)


@router.post("/prices", response_model=MarketPriceResponse, status_code=status.HTTP_201_CREATED)
async def add_price(
    body: MarketPriceCreate,
    repo: MarketRepository = Depends(get_market_repo),
) -> MarketPriceResponse:
    """Registra el precio de un ingrediente."""
    price = MarketPrice(
        id=0,
        ingredient_id=body.ingredient_id,
        price_ars=body.price_ars,
        source=body.source,
        store=body.store,
        confidence=body.confidence,
        date=body.date,
        created_at=datetime.utcnow(),
    )
    result = await repo.add_price(price)
    return MarketPriceResponse.model_validate(result.__dict__)


@router.get("/prices/current", response_model=list[MarketPriceResponse])
async def get_current_prices(
    repo: MarketRepository = Depends(get_market_repo),
) -> list[MarketPriceResponse]:
    """Retorna el precio más reciente de cada ingrediente."""
    prices = await repo.get_all_current_prices()
    return [MarketPriceResponse.model_validate(p.__dict__) for p in prices]


@router.get("/prices/history/{ingredient_id}", response_model=list[MarketPriceResponse])
async def get_price_history(
    ingredient_id: int,
    days: int = 30,
    repo: MarketRepository = Depends(get_market_repo),
) -> list[MarketPriceResponse]:
    """Retorna el historial de precios de un ingrediente (últimos N días)."""
    prices = await repo.get_price_history(ingredient_id, days)
    return [MarketPriceResponse.model_validate(p.__dict__) for p in prices]


@router.post("/pantry", response_model=PantryItemResponse, status_code=status.HTTP_201_CREATED)
async def update_pantry_item(
    body: PantryItemCreate,
    repo: MarketRepository = Depends(get_market_repo),
) -> PantryItemResponse:
    """Agrega o actualiza un ítem de la despensa (upsert por usuario + ingrediente)."""
    item = PantryItem(
        id=0,
        user_id=body.user_id,
        ingredient_id=body.ingredient_id,
        quantity_amount=body.quantity_amount,
        unit=body.unit,
        expires_at=body.expires_at,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    result = await repo.update_pantry(item)
    return PantryItemResponse.model_validate(result.__dict__)


@router.get("/pantry/{user_id}", response_model=list[PantryItemResponse])
async def get_pantry(
    user_id: int,
    repo: MarketRepository = Depends(get_market_repo),
) -> list[PantryItemResponse]:
    """Lista el inventario de la despensa de un usuario."""
    items = await repo.get_pantry(user_id)
    return [PantryItemResponse.model_validate(i.__dict__) for i in items]


@router.get(
    "/prices/cheapest/{ingredient_name}",
    response_model=CheapestPriceResponse,
    summary="Precio más barato de un ingrediente entre todos los supermercados",
)
async def get_cheapest_price(
    ingredient_name: str,
    days: int = Query(default=7, ge=1, le=90, description="Ventana de días a considerar"),
    market_repo: MarketRepository = Depends(get_market_repo),
    ing_repo: IngredientRepository = Depends(get_ingredient_repo),
) -> CheapestPriceResponse:
    """Retorna el precio más económico registrado para un ingrediente en los últimos N días,
    con comparativa por supermercado. Útil para que Ana informe dónde conviene comprar.
    """
    matches = await ing_repo.search_ingredients(ingredient_name)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingrediente '{ingredient_name}' no encontrado.",
        )
    ingredient = matches[0]

    prices = await market_repo.get_prices_last_n_days(ingredient.id, days=days)
    if not prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sin precios registrados para '{ingredient.name}' en los últimos {days} días.",
        )

    # Precio más barato por supermercado (el más reciente de cada store)
    seen_stores: dict[str | None, MarketPrice] = {}
    for p in sorted(prices, key=lambda x: x.date, reverse=True):
        if p.store not in seen_stores:
            seen_stores[p.store] = p

    store_comparison = sorted(
        [
            StorePrice(store=p.store, price_ars=p.price_ars, date=p.date, source=p.source)
            for p in seen_stores.values()
        ],
        key=lambda s: s.price_ars,
    )

    cheapest = store_comparison[0]
    return CheapestPriceResponse(
        ingredient_name=ingredient.name,
        ingredient_id=ingredient.id,
        cheapest_price_ars=cheapest.price_ars,
        cheapest_store=cheapest.store,
        cheapest_date=cheapest.date,
        store_comparison=store_comparison,
        days_analyzed=days,
    )


@router.get(
    "/prices/history/by-name/{ingredient_name}",
    response_model=PriceHistoryStats,
    summary="Historial de precios con estadísticas por nombre de ingrediente",
)
async def get_price_history_by_name(
    ingredient_name: str,
    days: int = Query(default=90, ge=1, le=365, description="Ventana de días a consultar"),
    market_repo: MarketRepository = Depends(get_market_repo),
    ing_repo: IngredientRepository = Depends(get_ingredient_repo),
) -> PriceHistoryStats:
    """Retorna el historial de precios de un ingrediente con promedio, mínimo y máximo.
    Diseñado para que Ana responda consultas del tipo '¿es buen precio?'.
    """
    matches = await ing_repo.search_ingredients(ingredient_name)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingrediente '{ingredient_name}' no encontrado.",
        )
    ingredient = matches[0]

    history = await market_repo.get_price_history(ingredient.id, days=days)

    avg_ars: float | None = None
    min_ars: float | None = None
    max_ars: float | None = None

    if history:
        price_values = [p.price_ars for p in history]
        avg_ars = round(mean(price_values), 2)
        min_ars = round(min(price_values), 2)
        max_ars = round(max(price_values), 2)

    return PriceHistoryStats(
        ingredient_name=ingredient.name,
        ingredient_id=ingredient.id,
        days_analyzed=days,
        total_records=len(history),
        avg_ars=avg_ars,
        min_ars=min_ars,
        max_ars=max_ars,
        history=[MarketPriceResponse.model_validate(p.__dict__) for p in history],
    )
