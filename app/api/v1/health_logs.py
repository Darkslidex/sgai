"""Endpoints CRUD para registros de salud."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.health_repo import HealthRepository
from app.api.schemas.health import HealthLogCreate, HealthLogResponse, WeeklyAvgResponse
from app.database import get_db
from app.domain.models.health import HealthLog

router = APIRouter(prefix="/health", tags=["health-logs"])


def get_health_repo(db: AsyncSession = Depends(get_db)) -> HealthRepository:
    return HealthRepository(db)


@router.post("/log", response_model=HealthLogResponse, status_code=status.HTTP_201_CREATED)
async def log_health(
    body: HealthLogCreate,
    repo: HealthRepository = Depends(get_health_repo),
) -> HealthLogResponse:
    """Registra datos de salud manualmente."""
    log = HealthLog(
        id=0,
        user_id=body.user_id,
        date=body.date,
        sleep_score=body.sleep_score,
        stress_level=body.stress_level,
        hrv=body.hrv,
        steps=body.steps,
        mood=body.mood,
        notes=body.notes,
        source=body.source,
        created_at=datetime.utcnow(),
    )
    result = await repo.log_health(log)
    return HealthLogResponse.model_validate(result.__dict__)


@router.get("/logs/{user_id}", response_model=list[HealthLogResponse])
async def get_logs(
    user_id: int,
    start: date = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    end: date = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    repo: HealthRepository = Depends(get_health_repo),
) -> list[HealthLogResponse]:
    """Lista logs de salud de un usuario en un rango de fechas."""
    logs = await repo.get_logs(user_id, start, end)
    return [HealthLogResponse.model_validate(l.__dict__) for l in logs]


@router.get("/latest/{user_id}", response_model=HealthLogResponse)
async def get_latest_log(
    user_id: int,
    repo: HealthRepository = Depends(get_health_repo),
) -> HealthLogResponse:
    """Obtiene el último registro de salud del usuario."""
    log = await repo.get_latest_log(user_id)
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay registros de salud")
    return HealthLogResponse.model_validate(log.__dict__)
