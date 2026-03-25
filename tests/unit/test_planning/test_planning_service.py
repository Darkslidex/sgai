"""Tests unitarios del PlanningService (mocks de repos y AI adapter)."""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models.planning import WeeklyPlan
from app.domain.models.user import UserProfile
from app.domain.ports.ai_planner_port import DayMeals, ShoppingItem, WeeklyPlanResult
from app.domain.services.planning_service import PlanningService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_profile(user_id: int = 1) -> UserProfile:
    return UserProfile(
        id=user_id, telegram_chat_id="123", name="Felix",
        age=42, weight_kg=80.0, height_cm=175.0,
        activity_level="moderate", goal="maintain",
        max_storage_volume={"refrigerados": 50, "secos": 30, "congelados": 20},
        created_at=datetime.now(), updated_at=datetime.now(),
    )


def _make_active_plan(user_id: int = 1, expired: bool = False) -> WeeklyPlan:
    expires_at = datetime.now() + (timedelta(days=-1) if expired else timedelta(days=6))
    return WeeklyPlan(
        id=1, user_id=user_id, week_start=date.today(),
        plan_json={"days": [{"day": "Lunes", "lunch": "Pollo", "dinner": "Arroz"}]},
        shopping_list_json={"items": []},
        total_cost_ars=12000.0, is_active=True,
        created_at=datetime.now(), expires_at=expires_at,
    )


def _make_ai_result() -> WeeklyPlanResult:
    return WeeklyPlanResult(
        days=[DayMeals(day="Lunes", lunch="Pollo al limón", dinner="Arroz con verduras")],
        shopping_list=[ShoppingItem("pollo", 2.0, "kg", 2400.0)],
        total_cost_ars=12000.0,
        cooking_day="Domingo",
        prep_steps=["1. Cocinar arroz", "2. Hornear pollo"],
        tokens_used=500,
    )


def _make_service(
    active_plan=None,
    ai_result=None,
    profile=None,
) -> tuple[PlanningService, MagicMock]:
    user_repo = AsyncMock()
    user_repo.get_profile.return_value = profile or _make_profile()
    user_repo.get_preferences.return_value = []

    market_repo = AsyncMock()
    market_repo.get_pantry.return_value = []
    market_repo.get_all_current_prices.return_value = []

    planning_repo = AsyncMock()
    planning_repo.get_active_plan.return_value = active_plan
    planning_repo.get_plan_history.return_value = []
    planning_repo.save_plan.side_effect = lambda p: p

    ing_repo = AsyncMock()
    ing_repo.list_ingredients.return_value = []

    ai_adapter = AsyncMock()
    ai_adapter.generate_plan.return_value = ai_result or _make_ai_result()

    service = PlanningService(user_repo, market_repo, planning_repo, ai_adapter, ing_repo)
    return service, ai_adapter


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_returns_cached_plan_if_active():
    """Si hay plan activo no expirado → retorna sin llamar a la IA."""
    active_plan = _make_active_plan()
    service, ai_adapter = _make_service(active_plan=active_plan)

    result = await service.get_or_generate_plan(user_id=1)

    ai_adapter.generate_plan.assert_not_called()
    assert result.id == active_plan.id


@pytest.mark.asyncio
async def test_generates_plan_when_no_cache():
    """Sin plan activo → la IA es llamada exactamente una vez."""
    service, ai_adapter = _make_service(active_plan=None)

    await service.get_or_generate_plan(user_id=1)

    ai_adapter.generate_plan.assert_called_once()


@pytest.mark.asyncio
async def test_generates_plan_when_plan_expired():
    """Plan expirado → la IA debe ser llamada (no usar caché vencida)."""
    expired_plan = _make_active_plan(expired=True)
    service, ai_adapter = _make_service(active_plan=expired_plan)

    await service.get_or_generate_plan(user_id=1)

    ai_adapter.generate_plan.assert_called_once()


@pytest.mark.asyncio
async def test_force_regenerate_ignores_cache():
    """force=True → la IA es llamada aunque haya plan activo válido."""
    active_plan = _make_active_plan()
    service, ai_adapter = _make_service(active_plan=active_plan)

    await service.get_or_generate_plan(user_id=1, force=True)

    ai_adapter.generate_plan.assert_called_once()


@pytest.mark.asyncio
async def test_persists_plan_after_generation():
    """El plan generado se pasa a planning_repo.save_plan."""
    service, _ = _make_service(active_plan=None)

    # Acceder al repo para verificar llamada
    await service.get_or_generate_plan(user_id=1)

    service._planning_repo.save_plan.assert_called_once()


@pytest.mark.asyncio
async def test_raises_if_user_not_found():
    """Si el usuario no existe en DB → ValueError."""
    service, _ = _make_service()
    service._user_repo.get_profile.return_value = None
    service._planning_repo.get_active_plan.return_value = None  # No cache

    with pytest.raises(ValueError, match="no encontrado"):
        await service.get_or_generate_plan(user_id=99)


@pytest.mark.asyncio
async def test_max_storage_volume_warning_logged(caplog):
    """ADR-008: Plan con lista de compras masiva genera WARNING de storage."""
    import logging

    # Plan con muchos items que exceden el storage
    big_result = WeeklyPlanResult(
        days=[DayMeals("Lunes", "X", "Y")],
        shopping_list=[ShoppingItem(f"item{i}", 100.0, "kg", 1000.0) for i in range(10)],
        total_cost_ars=50000.0,
        cooking_day="Domingo",
        prep_steps=[],
        tokens_used=100,
    )

    service, ai_adapter = _make_service(active_plan=None, ai_result=big_result)
    ai_adapter.generate_plan.return_value = big_result

    with caplog.at_level(logging.WARNING, logger="app.domain.services.planning_service"):
        await service.get_or_generate_plan(user_id=1)

    assert any("ADR-008" in r.message or "almacenamiento" in r.message for r in caplog.records)
