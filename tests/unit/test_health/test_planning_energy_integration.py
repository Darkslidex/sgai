"""Tests de integración entre PlanningService y EnergyModeService (ADR-008)."""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

from app.domain.models.health import HealthLog
from app.domain.models.recipe import Recipe
from app.domain.models.user import UserProfile
from app.domain.services.energy_mode_service import EnergyModeService, EnergyState
from app.domain.services.health_service import HealthService
from app.domain.services.planning_service import DailySuggestion, PlanningService


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_profile() -> UserProfile:
    return UserProfile(
        id=1, telegram_chat_id="123", name="Felix",
        age=42, weight_kg=80.0, height_cm=178.0,
        activity_level="moderate", goal="maintain",
        max_storage_volume={"refrigerados": 50, "secos": 30, "congelados": 20},
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )


def _make_recipe(id: int, name: str, prep_time_minutes: int = 30) -> Recipe:
    return Recipe(
        id=id, name=name, description="", prep_time_minutes=prep_time_minutes,
        is_batch_friendly=True, reheatable_days=5, servings=5,
        calories_per_serving=400.0, protein_per_serving=30.0,
        carbs_per_serving=40.0, fat_per_serving=10.0,
        instructions="[]", tags=[], created_at=datetime(2026, 1, 1),
    )


def _make_health_log(hrv=None, sleep_score=None, stress_level=None) -> HealthLog:
    return HealthLog(
        id=1, user_id=1, date=date(2026, 3, 19),
        sleep_score=sleep_score, stress_level=stress_level, hrv=hrv,
        steps=None, mood=None, notes=None, source="manual",
        created_at=datetime(2026, 3, 19),
    )


def _make_service(profile, metrics) -> PlanningService:
    """Construye PlanningService con mocks."""
    user_repo = AsyncMock()
    user_repo.get_profile.return_value = profile

    health_adapter = AsyncMock()
    health_adapter.get_latest_metrics.return_value = metrics

    # Repos no usados en get_todays_suggestion
    return PlanningService(
        user_repo=user_repo,
        market_repo=AsyncMock(),
        planning_repo=AsyncMock(),
        ai_planner=AsyncMock(),
        ingredient_repo=AsyncMock(),
        health_adapter=health_adapter,
        energy_mode_service=EnergyModeService(),
        health_service=HealthService(),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_todays_suggestion_normal_state_returns_all_recipes():
    """Con estado NORMAL, retorna todas las recetas disponibles."""
    profile = _make_profile()
    metrics = _make_health_log(hrv=60, sleep_score=80, stress_level=3)
    recipes = [
        _make_recipe(1, "Lentejas", prep_time_minutes=45),
        _make_recipe(2, "Pollo", prep_time_minutes=60),
    ]

    service = _make_service(profile, metrics)
    suggestion = await service.get_todays_suggestion(1, recipes)

    assert isinstance(suggestion, DailySuggestion)
    assert suggestion.energy_state == EnergyState.NORMAL
    assert len(suggestion.recipes) == 2


@pytest.mark.asyncio
async def test_get_todays_suggestion_low_energy_filters_recipes():
    """Con estado LOW, solo retorna recetas ≤10 min."""
    profile = _make_profile()
    metrics = _make_health_log(hrv=35, sleep_score=70)  # LOW: HRV bajo
    recipes = [
        _make_recipe(1, "Rapida", prep_time_minutes=5),
        _make_recipe(2, "Lenta", prep_time_minutes=60),
        _make_recipe(3, "Media", prep_time_minutes=10),
    ]

    service = _make_service(profile, metrics)
    suggestion = await service.get_todays_suggestion(1, recipes)

    assert suggestion.energy_state == EnergyState.LOW
    assert all(r.prep_time_minutes <= 10 for r in suggestion.recipes)
    assert len(suggestion.recipes) == 2


@pytest.mark.asyncio
async def test_get_todays_suggestion_critical_prioritizes_batch():
    """Con estado CRITICAL, se filtran recetas muy cortas o batch."""
    profile = _make_profile()
    metrics = _make_health_log(hrv=35, sleep_score=45)  # CRITICAL
    recipes = [
        _make_recipe(1, "Solo recalentar", prep_time_minutes=5),
        _make_recipe(2, "Cocinar 1h", prep_time_minutes=60),
        _make_recipe(3, "Cocinar 45min", prep_time_minutes=45),
    ]

    service = _make_service(profile, metrics)
    suggestion = await service.get_todays_suggestion(1, recipes)

    assert suggestion.energy_state == EnergyState.CRITICAL
    # En modo crítico, el filter aplica igual que LOW (≤10 min)
    assert all(r.prep_time_minutes <= 10 for r in suggestion.recipes)


@pytest.mark.asyncio
async def test_get_todays_suggestion_includes_tdee():
    """La sugerencia diaria siempre incluye TDEEResult."""
    profile = _make_profile()
    metrics = _make_health_log(hrv=60, sleep_score=80)

    service = _make_service(profile, metrics)
    suggestion = await service.get_todays_suggestion(1, [_make_recipe(1, "Receta", 30)])

    assert suggestion.tdee is not None
    assert suggestion.tdee.tdee > 0


@pytest.mark.asyncio
async def test_get_todays_suggestion_no_health_adapter_is_normal():
    """Sin health_adapter, el estado es siempre NORMAL."""
    profile = _make_profile()
    user_repo = AsyncMock()
    user_repo.get_profile.return_value = profile

    # Sin health_adapter
    service = PlanningService(
        user_repo=user_repo,
        market_repo=AsyncMock(),
        planning_repo=AsyncMock(),
        ai_planner=AsyncMock(),
        ingredient_repo=AsyncMock(),
        health_adapter=None,
    )

    recipes = [_make_recipe(1, "Receta", 60)]
    suggestion = await service.get_todays_suggestion(1, recipes)

    assert suggestion.energy_state == EnergyState.NORMAL


@pytest.mark.asyncio
async def test_get_todays_suggestion_raises_if_user_not_found():
    """Lanza ValueError si el usuario no existe."""
    user_repo = AsyncMock()
    user_repo.get_profile.return_value = None

    service = PlanningService(
        user_repo=user_repo,
        market_repo=AsyncMock(),
        planning_repo=AsyncMock(),
        ai_planner=AsyncMock(),
        ingredient_repo=AsyncMock(),
    )

    with pytest.raises(ValueError, match="no encontrado"):
        await service.get_todays_suggestion(99, [])
