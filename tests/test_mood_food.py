"""Tests del servicio MoodFoodService."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.mood_food_service import MoodFoodService, _pearson


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_health_log(day_offset: int, sleep: float = 70.0, stress: float = 5.0, hrv: float = 45.0):
    log = MagicMock()
    log.date = date.today() - timedelta(days=day_offset)
    log.sleep_score = sleep
    log.stress_level = stress
    log.hrv = hrv
    log.steps = 7000
    return log


def _make_plan(week_offset: int, cost: float = 15000.0):
    plan = MagicMock()
    plan.week_start = date.today() - timedelta(weeks=week_offset)
    plan.total_cost_ars = cost
    return plan


# ── has_enough_data ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_has_enough_data_with_2_weeks_returns_false():
    """2 semanas de datos → has_enough_data retorna (False, 2)."""
    health_repo = AsyncMock()
    # Logs en 2 semanas distintas
    logs = [_make_health_log(3), _make_health_log(10)]
    health_repo.get_logs.return_value = logs

    service = MoodFoodService(health_repo, AsyncMock(), llm=None)
    has_data, weeks = await service.has_enough_data(user_id=1)

    assert has_data is False
    assert weeks == 2


@pytest.mark.asyncio
async def test_has_enough_data_with_5_weeks_returns_true():
    """5 semanas de datos → has_enough_data retorna (True, 5)."""
    health_repo = AsyncMock()
    # Un log por semana durante 5 semanas
    logs = [_make_health_log(i * 7 + 1) for i in range(5)]
    health_repo.get_logs.return_value = logs

    service = MoodFoodService(health_repo, AsyncMock(), llm=None)
    has_data, weeks = await service.has_enough_data(user_id=1)

    assert has_data is True
    assert weeks == 5


# ── calculate_correlations ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calculate_correlations_values_between_minus1_and_1():
    """Las correlaciones calculadas están siempre en el rango [-1, 1]."""
    health_repo = AsyncMock()
    planning_repo = AsyncMock()

    # 8 semanas de logs
    logs = [_make_health_log(i * 7 + 1, sleep=60 + i * 3, stress=8 - i, hrv=35 + i * 2)
            for i in range(8)]
    health_repo.get_logs.return_value = logs
    planning_repo.get_plan_history.return_value = [_make_plan(i) for i in range(8)]

    service = MoodFoodService(health_repo, planning_repo, llm=None)
    result = await service.calculate_correlations(user_id=1)

    assert "correlations" in result
    for key, val in result["correlations"].items():
        if val is not None:
            assert -1.0 <= val <= 1.0, f"Correlación {key} fuera de rango: {val}"


# ── generate_insights ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_insights_returns_at_most_5():
    """generate_insights retorna máximo 5 insights."""
    health_repo = AsyncMock()
    planning_repo = AsyncMock()
    llm = AsyncMock()

    # 5 semanas de datos
    logs = [_make_health_log(i * 7 + 1) for i in range(5)]
    health_repo.get_logs.return_value = logs
    planning_repo.get_plan_history.return_value = [_make_plan(i) for i in range(5)]

    # LLM retorna 7 insights (debe truncarse a 5)
    llm.generate_text = AsyncMock(return_value='{"insights": [' +
        ','.join(['{"insight":"i","confidence":"high","recommendation":"r","data_points":4}'] * 7) +
        ']}')

    service = MoodFoodService(health_repo, planning_repo, llm)
    insights = await service.generate_insights(user_id=1)

    assert len(insights) <= 5


@pytest.mark.asyncio
async def test_generate_insights_returns_empty_without_enough_data():
    """Sin suficientes datos, generate_insights retorna lista vacía."""
    health_repo = AsyncMock()
    health_repo.get_logs.return_value = []

    service = MoodFoodService(health_repo, AsyncMock(), llm=AsyncMock())
    insights = await service.generate_insights(user_id=1)

    assert insights == []


# ── get_weekly_report ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_weekly_report_includes_required_fields():
    """get_weekly_report incluye todos los campos requeridos."""
    health_repo = AsyncMock()
    planning_repo = AsyncMock()

    health_repo.get_logs.return_value = [_make_health_log(1)]
    planning_repo.get_plan_history.return_value = [_make_plan(0)]

    service = MoodFoodService(health_repo, planning_repo, llm=None)
    report = await service.get_weekly_report(user_id=1)

    assert "week" in report
    assert "health_summary" in report
    assert "plan_summary" in report
    assert "avg_sleep" in report["health_summary"]
    assert "avg_stress" in report["health_summary"]
    assert "avg_steps" in report["health_summary"]
    assert "cost_ars" in report["plan_summary"]


# ── _pearson ──────────────────────────────────────────────────────────────────

def test_pearson_perfect_positive_correlation():
    """Correlación perfecta positiva retorna 1.0."""
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert abs(_pearson(x, x) - 1.0) < 1e-9


def test_pearson_perfect_negative_correlation():
    """Correlación perfecta negativa retorna -1.0."""
    x = [1.0, 2.0, 3.0]
    y = [3.0, 2.0, 1.0]
    assert abs(_pearson(x, y) + 1.0) < 1e-9


def test_pearson_insufficient_data_returns_none():
    """Menos de 2 puntos retorna None."""
    assert _pearson([1.0], [1.0]) is None
    assert _pearson([], []) is None
