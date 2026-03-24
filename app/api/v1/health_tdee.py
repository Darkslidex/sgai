"""
Endpoints de TDEE dinámico y Modo Baja Energía (ADR-008).

GET /api/v1/health/tdee/{user_id}         → TDEE con breakdown completo
GET /api/v1/health/energy-state/{user_id} → Estado energético actual
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.health.manual_health_adapter import ManualHealthAdapter
from app.adapters.persistence.health_repo import HealthRepository
from app.adapters.persistence.user_repo import UserRepository
from app.database import get_db
from app.domain.services.energy_mode_service import EnergyModeService, EnergyState
from app.domain.services.health_service import HealthService, TDEEResult

router = APIRouter(prefix="/health", tags=["health-tdee"])


# ── Response schemas ──────────────────────────────────────────────────────────

class TDEEResponse(BaseModel):
    user_id: int
    bmr: float
    activity_multiplier: float
    goal_multiplier: float
    stress_adjustment: float
    sleep_adjustment: float
    tdee: int
    breakdown: dict
    has_biometric_data: bool


class EnergyStateResponse(BaseModel):
    user_id: int
    energy_state: EnergyState
    hrv: float | None
    sleep_score: float | None
    stress_level: float | None
    message: str


# ── Dependency helpers ────────────────────────────────────────────────────────

def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_health_adapter(db: AsyncSession = Depends(get_db)) -> ManualHealthAdapter:
    return ManualHealthAdapter(db)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/tdee/{user_id}", response_model=TDEEResponse)
async def get_tdee(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repo),
    health_adapter: ManualHealthAdapter = Depends(get_health_adapter),
) -> TDEEResponse:
    """
    Calcula el TDEE dinámico con ajustes por biomarcadores.

    Usa Harris-Benedict revisado + ajuste por actividad/objetivo/estrés/sueño.
    """
    profile = await user_repo.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario {user_id} no encontrado",
        )

    metrics = await health_adapter.get_latest_metrics(user_id)

    service = HealthService()
    result = service.calculate_tdee(profile, metrics)

    return TDEEResponse(
        user_id=user_id,
        bmr=result.bmr,
        activity_multiplier=result.activity_multiplier,
        goal_multiplier=result.goal_multiplier,
        stress_adjustment=result.stress_adjustment,
        sleep_adjustment=result.sleep_adjustment,
        tdee=result.tdee,
        breakdown=result.breakdown,
        has_biometric_data=metrics is not None,
    )


@router.get("/energy-state/{user_id}", response_model=EnergyStateResponse)
async def get_energy_state(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repo),
    health_adapter: ManualHealthAdapter = Depends(get_health_adapter),
) -> EnergyStateResponse:
    """
    Evalúa el estado energético actual del usuario (ADR-008).

    - NORMAL: Flujo completo disponible
    - LOW: Modo Baja Energía activado (recetas ≤10 min)
    - CRITICAL: Baja Energía extrema (solo recalentar batch)
    """
    profile = await user_repo.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario {user_id} no encontrado",
        )

    metrics = await health_adapter.get_latest_metrics(user_id)

    energy_service = EnergyModeService()
    state = await energy_service.evaluate_energy_state(user_id, metrics)

    _messages = {
        EnergyState.NORMAL: "Estado energético normal. Flujo completo disponible.",
        EnergyState.LOW: "Modo Baja Energía activo. Se priorizan recetas ≤10 min.",
        EnergyState.CRITICAL: "Energía crítica. Solo recalentá batch ya preparado. Descansá.",
    }

    return EnergyStateResponse(
        user_id=user_id,
        energy_state=state,
        hrv=metrics.hrv if metrics else None,
        sleep_score=metrics.sleep_score if metrics else None,
        stress_level=metrics.stress_level if metrics else None,
        message=_messages[state],
    )
