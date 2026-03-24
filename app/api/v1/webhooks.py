"""Endpoints webhook para Ana (OpenClaw) → SGAI.

Ana llama estos endpoints para:
- Enviar datos de salud parseados de lenguaje natural o Google Fit.
- Enviar ítems de un ticket de compra (ya parseados por DeepSeek Vision).
- Consultar si un precio es conveniente comparado con el histórico.

Autenticación: header X-Ana-Key con el valor de ANA_API_KEY en .env.
"""

from datetime import date, datetime
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.health_repo import HealthRepository
from app.adapters.persistence.ingredient_repo import IngredientRepository
from app.adapters.persistence.market_repo import MarketRepository
from app.adapters.persistence.user_repo import UserRepository
from app.api.dependencies.auth import verify_ana_api_key
from app.database import get_db
from app.domain.models.health import HealthLog
from app.domain.services.health_service import HealthService
from app.domain.services.receipt_service import ReceiptService

router = APIRouter(
    prefix="/webhooks/ana",
    tags=["webhooks-ana"],
    dependencies=[Depends(verify_ana_api_key)],
)


# ── Schemas de entrada ────────────────────────────────────────────────────────


class HealthLogFromAna(BaseModel):
    """Datos de salud que Ana parsea desde lenguaje natural o Google Fit."""

    user_id: int
    date: date
    sleep_hours: float | None = Field(None, ge=0, le=24, description="Horas de sueño")
    stress_level: float | None = Field(None, ge=0, le=10)
    steps: int | None = Field(None, ge=0)
    hrv: float | None = Field(None, ge=0)


class ReceiptItem(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    price_ars: float = Field(gt=0, le=1_000_000)
    quantity: float = Field(default=1.0, gt=0)


class ReceiptFromAna(BaseModel):
    """Ticket de compra parseado por DeepSeek Vision en Ana."""

    store_name: str = Field(min_length=1, max_length=100)
    purchase_date: date = Field(default_factory=date.today)
    items: list[ReceiptItem] = Field(min_length=1)


class PriceCheckFromAna(BaseModel):
    """Consulta de conveniencia de precio."""

    ingredient_name: str = Field(min_length=1, max_length=200)
    price_ars: float = Field(gt=0, le=1_000_000)
    store: str | None = Field(None, max_length=100)


# ── Schemas de respuesta ──────────────────────────────────────────────────────


class HealthLogResult(BaseModel):
    ok: bool
    health_log_id: int
    sleep_score: float | None
    message: str


class ReceiptResult(BaseModel):
    ok: bool
    registered: int
    skipped: int
    skipped_items: list[str]
    message: str


class PriceCheckResult(BaseModel):
    ok: bool
    ingredient_name: str
    ingredient_id: int | None
    queried_price_ars: float
    store: str | None
    historical_avg_ars: float | None
    historical_min_ars: float | None
    historical_max_ars: float | None
    verdict: str
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/health-log",
    response_model=HealthLogResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ana envía datos de salud",
)
async def receive_health_log(
    body: HealthLogFromAna,
    db: AsyncSession = Depends(get_db),
) -> HealthLogResult:
    """Registra un log de salud enviado por Ana.

    Ana puede enviar sleep_hours (ej. 7.5) y SGAI lo convierte a sleep_score (0-100)
    usando la fórmula: sleep_score = min(sleep_hours / 9.0 * 100, 100).
    """
    sleep_score: float | None = None
    if body.sleep_hours is not None:
        sleep_score = round(min(body.sleep_hours / 9.0 * 100, 100.0), 1)

    repo = HealthRepository(db)
    log = HealthLog(
        id=0,
        user_id=body.user_id,
        date=body.date,
        sleep_score=sleep_score,
        stress_level=body.stress_level,
        hrv=body.hrv,
        steps=body.steps,
        mood=None,
        notes="Registrado por Ana",
        source="health_connect",
        created_at=datetime.utcnow(),
    )
    result = await repo.log_health(log)

    return HealthLogResult(
        ok=True,
        health_log_id=result.id,
        sleep_score=sleep_score,
        message=f"Log de salud registrado para user_id={body.user_id} en fecha {body.date}.",
    )


@router.post(
    "/receipt",
    response_model=ReceiptResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ana envía un ticket de compra parseado",
)
async def receive_receipt(
    body: ReceiptFromAna,
    db: AsyncSession = Depends(get_db),
) -> ReceiptResult:
    """Procesa un ticket de compra ya parseado por DeepSeek Vision en Ana.

    Usa ReceiptService con fuzzy matching pg_trgm (fallback a ILIKE + Python).
    Los ítems sin match se reportan como skipped para que Ana informe al usuario.
    """
    service = ReceiptService(
        ingredient_repo=IngredientRepository(db),
        market_repo=MarketRepository(db),
    )
    items_dicts = [
        {"product_name": item.product_name, "price_ars": item.price_ars, "quantity": item.quantity}
        for item in body.items
    ]
    result = await service.process_items(
        store_name=body.store_name,
        purchase_date=body.purchase_date,
        items=items_dicts,
    )

    message = f"{result.registered} precio(s) registrado(s)"
    message += f", {result.skipped} ítem(s) sin match en la DB." if result.skipped else "."

    return ReceiptResult(
        ok=True,
        registered=result.registered,
        skipped=result.skipped,
        skipped_items=result.skipped_items,
        message=message,
    )


@router.post(
    "/price-check",
    response_model=PriceCheckResult,
    summary="Ana consulta si un precio es conveniente",
)
async def check_price(
    body: PriceCheckFromAna,
    db: AsyncSession = Depends(get_db),
) -> PriceCheckResult:
    """Compara un precio consultado con el histórico de SGAI.

    Devuelve promedio, mínimo y máximo histórico, y un veredicto:
    - 'conveniente': precio <= promedio histórico
    - 'caro': precio > promedio histórico pero <= máximo
    - 'muy_caro': precio > máximo histórico registrado
    - 'sin_historial': no hay datos previos en la DB
    """
    ing_repo = IngredientRepository(db)
    market_repo = MarketRepository(db)

    matches = await ing_repo.search_ingredients(body.ingredient_name)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingrediente '{body.ingredient_name}' no encontrado en la DB.",
        )

    ingredient = matches[0]
    history = await market_repo.get_price_history(ingredient.id, days=90)

    if not history:
        return PriceCheckResult(
            ok=True,
            ingredient_name=ingredient.name,
            ingredient_id=ingredient.id,
            queried_price_ars=body.price_ars,
            store=body.store,
            historical_avg_ars=None,
            historical_min_ars=None,
            historical_max_ars=None,
            verdict="sin_historial",
            message=f"No hay historial de precios para '{ingredient.name}'. Precio guardado como referencia.",
        )

    prices = [p.price_ars for p in history]
    avg = round(mean(prices), 2)
    minimum = round(min(prices), 2)
    maximum = round(max(prices), 2)

    if body.price_ars <= avg:
        verdict = "conveniente"
    elif body.price_ars <= maximum:
        verdict = "caro"
    else:
        verdict = "muy_caro"

    message = (
        f"'{ingredient.name}': precio consultado ARS {body.price_ars:.2f} vs "
        f"promedio histórico ARS {avg:.2f} (min {minimum:.2f} / max {maximum:.2f}). "
        f"Veredicto: {verdict}."
    )

    return PriceCheckResult(
        ok=True,
        ingredient_name=ingredient.name,
        ingredient_id=ingredient.id,
        queried_price_ars=body.price_ars,
        store=body.store,
        historical_avg_ars=avg,
        historical_min_ars=minimum,
        historical_max_ars=maximum,
        verdict=verdict,
        message=message,
    )


# ── Biometrics (Google Fit) ───────────────────────────────────────────────────


class BiometricsFromAna(BaseModel):
    """Datos biométricos diarios obtenidos por Ana desde Google Fit REST API."""

    user_id: int
    date: date
    sleep_hours: float | None = Field(None, ge=0, le=24)
    deep_sleep_minutes: int | None = Field(None, ge=0)
    steps: int | None = Field(None, ge=0)
    heart_rate_avg: float | None = Field(None, ge=20, le=250)
    hrv: float | None = Field(None, ge=0)


class BiometricsResult(BaseModel):
    ok: bool
    health_log_id: int
    sleep_score: float | None
    tdee_kcal: int | None
    message: str


@router.post(
    "/biometrics",
    response_model=BiometricsResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ana envía datos biométricos desde Google Fit",
)
async def receive_biometrics(
    body: BiometricsFromAna,
    db: AsyncSession = Depends(get_db),
) -> BiometricsResult:
    """Registra datos biométricos diarios obtenidos por Ana desde Google Fit REST API.

    Convierte sleep_hours → sleep_score, registra el log de salud y recalcula
    el TDEE dinámico con los nuevos biomarcadores. heart_rate_avg se registra
    en notes para referencia futura.
    """
    sleep_score: float | None = None
    if body.sleep_hours is not None:
        sleep_score = round(min(body.sleep_hours / 9.0 * 100, 100.0), 1)

    notes_parts = ["Biometría Google Fit"]
    if body.deep_sleep_minutes is not None:
        notes_parts.append(f"Sueño profundo: {body.deep_sleep_minutes} min")
    if body.heart_rate_avg is not None:
        notes_parts.append(f"FC media: {body.heart_rate_avg:.0f} bpm")

    health_repo = HealthRepository(db)
    log = HealthLog(
        id=0,
        user_id=body.user_id,
        date=body.date,
        sleep_score=sleep_score,
        stress_level=None,
        hrv=body.hrv,
        steps=body.steps,
        mood=None,
        notes=" | ".join(notes_parts),
        source="health_connect",
        created_at=datetime.utcnow(),
    )
    saved_log = await health_repo.log_health(log)

    # Recalcular TDEE con los nuevos biomarcadores
    tdee_kcal: int | None = None
    user_repo = UserRepository(db)
    profile = await user_repo.get_profile(body.user_id)
    if profile is not None:
        health_service = HealthService()
        tdee_result = health_service.calculate_tdee(profile, saved_log)
        tdee_kcal = tdee_result.tdee

    message = f"Biometría registrada para user_id={body.user_id} en {body.date}."
    if tdee_kcal:
        message += f" TDEE actualizado: {tdee_kcal} kcal/día."

    return BiometricsResult(
        ok=True,
        health_log_id=saved_log.id,
        sleep_score=sleep_score,
        tdee_kcal=tdee_kcal,
        message=message,
    )
