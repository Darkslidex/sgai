"""Endpoints CRUD para precios de mercado y despensa."""

from datetime import date, datetime
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.ingredient_repo import IngredientRepository
from app.adapters.persistence.market_repo import MarketRepository
from app.adapters.persistence.meal_log_repo import MealLogRepository
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
from app.domain.services.pantry_service import PantryService

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


# ── Schemas para consume y sync ───────────────────────────────────────────────


class ConsumeItemRequest(BaseModel):
    ingredient_name: str
    quantity_g: float


class ConsumeItemResponse(BaseModel):
    ingredient_name: str
    ingredient_id: int
    quantity_consumed_g: float
    quantity_remaining: float | None
    unit: str | None
    status: str  # "consumed", "depleted", "not_in_pantry", "not_found"


class SyncResult(BaseModel):
    ingredient: str
    quantity_consumed_g: float
    quantity_remaining: float | None
    unit: str | None
    status: str  # "consumed", "depleted", "not_in_pantry", "not_found"


class SyncFromMealsResponse(BaseModel):
    user_id: int
    start_date: str
    end_date: str
    results: list[SyncResult]
    total_consumed: int
    total_depleted: int
    total_not_in_pantry: int
    total_not_found: int


# ── Endpoint: consumir un ítem de la alacena ─────────────────────────────────


@router.post(
    "/pantry/{user_id}/consume",
    response_model=ConsumeItemResponse,
    summary="Descuenta un ingrediente de la alacena por nombre",
)
async def consume_pantry_item(
    user_id: int,
    body: ConsumeItemRequest,
    market_repo: MarketRepository = Depends(get_market_repo),
    ing_repo: IngredientRepository = Depends(get_ingredient_repo),
) -> ConsumeItemResponse:
    """Resta quantity_g del ingrediente en la alacena.

    Busca el ingrediente por nombre (fuzzy). Si la cantidad llega a 0 o menos,
    elimina el item de la alacena. Útil para que Ana descuente ingredientes
    específicos sin necesidad de calcular cantidades manualmente.
    """
    if body.quantity_g <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="quantity_g debe ser positiva.",
        )

    matches = await ing_repo.search_ingredients(body.ingredient_name)
    if not matches:
        return ConsumeItemResponse(
            ingredient_name=body.ingredient_name,
            ingredient_id=0,
            quantity_consumed_g=body.quantity_g,
            quantity_remaining=None,
            unit=None,
            status="not_found",
        )

    ingredient = matches[0]

    existing = await market_repo.get_pantry_item(user_id, ingredient.id)
    if existing is None:
        return ConsumeItemResponse(
            ingredient_name=ingredient.name,
            ingredient_id=ingredient.id,
            quantity_consumed_g=body.quantity_g,
            quantity_remaining=None,
            unit=ingredient.unit,
            status="not_in_pantry",
        )

    pantry_service = PantryService(market_repo, ing_repo)
    updated = await pantry_service.remove_item(user_id, ingredient.id, body.quantity_g)

    if updated is None:
        return ConsumeItemResponse(
            ingredient_name=ingredient.name,
            ingredient_id=ingredient.id,
            quantity_consumed_g=body.quantity_g,
            quantity_remaining=0.0,
            unit=ingredient.unit,
            status="depleted",
        )

    return ConsumeItemResponse(
        ingredient_name=ingredient.name,
        ingredient_id=ingredient.id,
        quantity_consumed_g=body.quantity_g,
        quantity_remaining=round(updated.quantity_amount, 2),
        unit=updated.unit,
        status="consumed",
    )


# ── Endpoint: sincronizar alacena desde meal_logs ────────────────────────────


@router.post(
    "/pantry/{user_id}/sync-from-meals",
    response_model=SyncFromMealsResponse,
    summary="Sincroniza la alacena descontando todo lo consumido en un rango de fechas",
)
async def sync_pantry_from_meals(
    user_id: int,
    start_date: date = Query(..., description="Fecha de inicio YYYY-MM-DD"),
    end_date: date = Query(..., description="Fecha de fin YYYY-MM-DD (inclusive)"),
    db: AsyncSession = Depends(get_db),
) -> SyncFromMealsResponse:
    """Lee los meal_logs del rango de fechas, agrega por ingrediente y descuenta de la alacena.

    Este es el endpoint principal para mantener la alacena sincronizada. Ana debe
    llamarlo con el rango de días donde hubo comidas registradas en lugar de intentar
    actualizar cada ingrediente manualmente.

    - status=consumed: se descontó correctamente, quedan unidades.
    - status=depleted: se agotó completamente (eliminado de la alacena).
    - status=not_in_pantry: el ingrediente existe en la DB pero no estaba en la alacena.
    - status=not_found: el nombre del ingrediente no se encontró en la tabla de ingredientes.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date debe ser igual o posterior a start_date.",
        )

    meal_repo = MealLogRepository(db)
    market_repo = MarketRepository(db)
    ing_repo = IngredientRepository(db)
    pantry_service = PantryService(market_repo, ing_repo)

    consumed = await meal_repo.get_consumed_ingredients_range(user_id, start_date, end_date)

    results: list[SyncResult] = []
    for ingredient_name, total_g in consumed.items():
        matches = await ing_repo.search_ingredients(ingredient_name)
        if not matches:
            results.append(SyncResult(
                ingredient=ingredient_name,
                quantity_consumed_g=round(total_g, 1),
                quantity_remaining=None,
                unit=None,
                status="not_found",
            ))
            continue

        ingredient = matches[0]
        existing = await market_repo.get_pantry_item(user_id, ingredient.id)
        if existing is None:
            results.append(SyncResult(
                ingredient=ingredient.name,
                quantity_consumed_g=round(total_g, 1),
                quantity_remaining=None,
                unit=ingredient.unit,
                status="not_in_pantry",
            ))
            continue

        updated = await pantry_service.remove_item(user_id, ingredient.id, total_g)
        if updated is None:
            results.append(SyncResult(
                ingredient=ingredient.name,
                quantity_consumed_g=round(total_g, 1),
                quantity_remaining=0.0,
                unit=ingredient.unit,
                status="depleted",
            ))
        else:
            results.append(SyncResult(
                ingredient=ingredient.name,
                quantity_consumed_g=round(total_g, 1),
                quantity_remaining=round(updated.quantity_amount, 2),
                unit=updated.unit,
                status="consumed",
            ))

    return SyncFromMealsResponse(
        user_id=user_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        results=results,
        total_consumed=sum(1 for r in results if r.status == "consumed"),
        total_depleted=sum(1 for r in results if r.status == "depleted"),
        total_not_in_pantry=sum(1 for r in results if r.status == "not_in_pantry"),
        total_not_found=sum(1 for r in results if r.status == "not_found"),
    )


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
