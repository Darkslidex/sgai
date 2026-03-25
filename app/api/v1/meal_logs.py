"""Endpoints de consulta de registros de consumo alimentario.

GET /api/v1/meal-logs/daily/{user_id}?date=YYYY-MM-DD
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.meal_log_repo import MealLogRepository
from app.adapters.persistence.user_repo import UserRepository
from app.database import get_db
from app.domain.services.health_service import HealthService

router = APIRouter(prefix="/meal-logs", tags=["meal-logs"])


# ── Response schemas ──────────────────────────────────────────────────────────


class MealItemSummary(BaseModel):
    ingredient: str
    quantity_g: float
    calories_kcal: float
    protein_g: float | None = None


class MealLogEntry(BaseModel):
    id: int
    meal_type: str
    raw_description: str
    items: list[MealItemSummary]
    total_calories_kcal: float
    total_protein_g: float | None
    source: str
    created_at: str


class DailySummaryResponse(BaseModel):
    date: str
    user_id: int
    total_calories_kcal: float
    total_protein_g: float | None
    tdee_kcal: int | None
    calories_remaining: float | None
    meals: list[MealLogEntry]


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get(
    "/daily/{user_id}",
    response_model=DailySummaryResponse,
    summary="Resumen diario de comidas registradas",
)
async def get_daily_summary(
    user_id: int,
    date: date = Query(..., description="Fecha a consultar en formato YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
) -> DailySummaryResponse:
    """Retorna todas las comidas registradas del día con totales y calorías restantes vs TDEE.

    - total_calories_kcal: suma de calorías de todas las comidas del día.
    - total_protein_g: suma de proteínas (null si no hay datos de proteínas).
    - tdee_kcal: TDEE calculado desde el perfil del usuario (sin ajustes biométricos).
    - calories_remaining: tdee_kcal - total_calories_kcal (puede ser negativo si se pasó).
    - meals: lista ordenada cronológicamente de todas las comidas del día.
    """
    user_repo = UserRepository(db)
    profile = await user_repo.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario {user_id} no encontrado.",
        )

    meal_repo = MealLogRepository(db)
    summary = await meal_repo.get_daily_summary(user_id, date)

    # Calcular TDEE desde perfil (sin métricas de salud en tiempo real)
    health_service = HealthService()
    tdee_result = health_service.calculate_tdee(profile, metrics=None)
    tdee_kcal = tdee_result.tdee
    calories_remaining = round(tdee_kcal - summary["total_calories_kcal"], 1)

    meals = [
        MealLogEntry(
            id=meal["id"],
            meal_type=meal["meal_type"],
            raw_description=meal["raw_description"],
            items=[
                MealItemSummary(
                    ingredient=item["ingredient"],
                    quantity_g=item["quantity_g"],
                    calories_kcal=item["calories_kcal"],
                    protein_g=item.get("protein_g"),
                )
                for item in meal["items"]
            ],
            total_calories_kcal=meal["total_calories_kcal"],
            total_protein_g=meal.get("total_protein_g"),
            source=meal["source"],
            created_at=meal["created_at"],
        )
        for meal in summary["meals"]
    ]

    return DailySummaryResponse(
        date=summary["date"],
        user_id=user_id,
        total_calories_kcal=summary["total_calories_kcal"],
        total_protein_g=summary["total_protein_g"],
        tdee_kcal=tdee_kcal,
        calories_remaining=calories_remaining,
        meals=meals,
    )
