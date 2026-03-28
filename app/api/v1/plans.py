"""Endpoints para planes de comidas semanales."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.planning_repo import PlanningRepository
from app.database import get_db

router = APIRouter(prefix="/plans", tags=["plans"])


class WeeklyPlanResponse(BaseModel):
    id: int
    user_id: int
    week_start: str
    plan_json: dict
    shopping_list_json: dict
    total_cost_ars: float | None
    is_active: bool
    expires_at: str | None


@router.get("/current", response_model=WeeklyPlanResponse, summary="Plan de comidas activo")
async def get_current_plan(db: AsyncSession = Depends(get_db)) -> WeeklyPlanResponse:
    """Retorna el plan de comidas semanal activo del usuario 1.

    Retorna 404 si no hay ningún plan activo generado aún.
    """
    repo = PlanningRepository(db)
    plan = await repo.get_active_plan(user_id=1)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay ningún plan de comidas activo. Generá uno desde el dashboard Streamlit.",
        )
    return WeeklyPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        week_start=plan.week_start.isoformat(),
        plan_json=plan.plan_json,
        shopping_list_json=plan.shopping_list_json,
        total_cost_ars=plan.total_cost_ars,
        is_active=plan.is_active,
        expires_at=plan.expires_at.isoformat() if plan.expires_at else None,
    )
