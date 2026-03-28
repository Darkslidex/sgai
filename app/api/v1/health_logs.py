"""Endpoints CRUD para registros de salud."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
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


# ── Inferencia de estrés desde HRV ────────────────────────────────────────────

from app.domain.services.stress_inference_service import StressInferenceService


class InferStressRequest(BaseModel):
    user_id: int


class InferStressResponse(BaseModel):
    stress_inferred: bool
    stress_score: int | None = None
    stress_label: str | None = None
    hrv_rmssd: float | None = None
    source: str
    reason: str | None = None
    action: str | None = None


@router.post(
    '/infer-stress',
    response_model=InferStressResponse,
    summary='Inferir estrés desde último HRV disponible',
)
async def infer_stress(
    body: InferStressRequest,
    db: AsyncSession = Depends(get_db),
    repo: HealthRepository = Depends(get_health_repo),
) -> InferStressResponse:
    '''Infiere y persiste el nivel de estres desde el HRV RMSSD del último health log.

    Si HRV disponible: calcula estres, actualiza el health_log con stress_level
    y stress_source=inferred_hrv. Si no hay HRV: retorna manual_input_required.
    '''
    from datetime import datetime

    log = await repo.get_latest_log(body.user_id)
    if log is None:
        return InferStressResponse(
            stress_inferred=False,
            source='manual_required',
            reason='no_health_log',
            action='Registrá datos de salud primero.',
        )

    score, source = StressInferenceService.infer_from_hrv(log.hrv)

    if score is None:
        return InferStressResponse(
            stress_inferred=False,
            source='manual_required',
            reason='no_hrv_data',
            action='¿Cómo te sentís del 1 al 10?',
        )

    # Actualizar el log existente con estrés inferido
    log.stress_level = float(score)
    log.notes = (log.notes or '') + ' | estrés inferido de HRV'
    await repo.upsert_daily_log(log)

    return InferStressResponse(
        stress_inferred=True,
        stress_score=score,
        stress_label=StressInferenceService.stress_label(score),
        hrv_rmssd=log.hrv,
        source=source,
    )
