"""Endpoints CRUD para precios de mercado y despensa."""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.market_repo import MarketRepository
from app.api.schemas.market import (
    MarketPriceCreate,
    MarketPriceResponse,
    PantryItemCreate,
    PantryItemResponse,
)
from app.database import get_db
from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem

router = APIRouter(prefix="/market", tags=["market"])


def get_market_repo(db: AsyncSession = Depends(get_db)) -> MarketRepository:
    return MarketRepository(db)


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
