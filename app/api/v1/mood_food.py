"""Endpoints Mood & Food — correlaciones y reporte semanal."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.health_repo import HealthRepository
from app.adapters.persistence.planning_repo import PlanningRepository
from app.database import get_db
from app.domain.services.mood_food_service import MoodFoodService

router = APIRouter(prefix="/mood-food", tags=["mood-food"])


def _make_service(db: AsyncSession) -> MoodFoodService:
    return MoodFoodService(
        health_repo=HealthRepository(db),
        planning_repo=PlanningRepository(db),
        llm=None,  # Sin LLM para endpoints de solo-datos
    )


class CorrelationsResponse(BaseModel):
    correlations: dict
    strongest_positive: dict
    strongest_negative: dict
    weeks_analyzed: int
    calculated_at: str


class WeeklyReportResponse(BaseModel):
    week: str
    health_summary: dict
    plan_summary: dict
    mood_food_insight: str | None
    recommendation_for_next_week: str | None


@router.get(
    "/correlations/{user_id}",
    response_model=CorrelationsResponse,
    summary="Correlaciones Mood & Food del usuario",
)
async def get_correlations(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> CorrelationsResponse:
    """Retorna correlaciones de Pearson entre sueño, estrés, HRV, pasos y costo del plan.

    Requiere mínimo 4 semanas de datos. Si no hay suficientes datos retorna 422.
    """
    service = _make_service(db)
    has_data, weeks = await service.has_enough_data(user_id)
    if not has_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Datos insuficientes para análisis: {weeks} semana(s) disponibles, mínimo 4.",
        )
    data = await service.calculate_correlations(user_id)
    return CorrelationsResponse(**data)


@router.get(
    "/report/{user_id}",
    response_model=WeeklyReportResponse,
    summary="Reporte semanal de salud y plan",
)
async def get_weekly_report(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> WeeklyReportResponse:
    """Retorna el reporte semanal consolidado: promedios de salud, costo del plan e insight principal."""
    service = _make_service(db)
    data = await service.get_weekly_report(user_id)
    return WeeklyReportResponse(**data)
