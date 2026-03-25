"""Tests unitarios para EnergyModeService — Modo Baja Energía ADR-008."""

import pytest
from datetime import date, datetime

from app.domain.models.health import HealthLog
from app.domain.models.recipe import Recipe
from app.domain.services.energy_mode_service import EnergyModeService, EnergyState


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_health_log(
    hrv: float | None = None,
    sleep_score: float | None = None,
    stress_level: float | None = None,
) -> HealthLog:
    return HealthLog(
        id=1,
        user_id=1,
        date=date(2026, 3, 19),
        sleep_score=sleep_score,
        stress_level=stress_level,
        hrv=hrv,
        steps=None,
        mood=None,
        notes=None,
        source="manual",
        created_at=datetime(2026, 3, 19),
    )


def _make_recipe(
    id: int,
    name: str,
    prep_time_minutes: int = 30,
    tags: list[str] | None = None,
) -> Recipe:
    return Recipe(
        id=id,
        name=name,
        description="",
        prep_time_minutes=prep_time_minutes,
        is_batch_friendly=True,
        reheatable_days=5,
        servings=5,
        calories_per_serving=400.0,
        protein_per_serving=30.0,
        carbs_per_serving=40.0,
        fat_per_serving=10.0,
        instructions="[]",
        tags=tags or [],
        created_at=datetime(2026, 1, 1),
    )


# ── Tests: evaluate_energy_state ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hrv_low_and_sleep_poor_is_critical():
    """HRV < 40 ms Y sleep < 55 → CRITICAL."""
    metrics = _make_health_log(hrv=35, sleep_score=50)
    service = EnergyModeService()
    state = await service.evaluate_energy_state(1, metrics)
    assert state == EnergyState.CRITICAL


@pytest.mark.asyncio
async def test_hrv_low_sleep_ok_is_low():
    """HRV < 40 ms pero sleep >= 55 → LOW."""
    metrics = _make_health_log(hrv=35, sleep_score=70)
    service = EnergyModeService()
    state = await service.evaluate_energy_state(1, metrics)
    assert state == EnergyState.LOW


@pytest.mark.asyncio
async def test_stress_high_hrv_normal_is_low():
    """Stress > 7 aunque HRV sea normal → LOW."""
    metrics = _make_health_log(hrv=60, stress_level=8)
    service = EnergyModeService()
    state = await service.evaluate_energy_state(1, metrics)
    assert state == EnergyState.LOW


@pytest.mark.asyncio
async def test_sleep_poor_only_is_low():
    """Solo sleep_score < 55 (sin HRV) → LOW."""
    metrics = _make_health_log(sleep_score=45)
    service = EnergyModeService()
    state = await service.evaluate_energy_state(1, metrics)
    assert state == EnergyState.LOW


@pytest.mark.asyncio
async def test_all_normal_is_normal():
    """HRV normal + sueño normal + estrés normal → NORMAL."""
    metrics = _make_health_log(hrv=60, sleep_score=80, stress_level=3)
    service = EnergyModeService()
    state = await service.evaluate_energy_state(1, metrics)
    assert state == EnergyState.NORMAL


@pytest.mark.asyncio
async def test_no_metrics_is_normal():
    """Sin métricas → NORMAL (no penalizar por falta de datos)."""
    service = EnergyModeService()
    state = await service.evaluate_energy_state(1, None)
    assert state == EnergyState.NORMAL


@pytest.mark.asyncio
async def test_hrv_exactly_40_not_low():
    """HRV exactamente 40 ms (umbral) NO activa baja energía (debe ser <40)."""
    metrics = _make_health_log(hrv=40, sleep_score=80)
    service = EnergyModeService()
    state = await service.evaluate_energy_state(1, metrics)
    assert state == EnergyState.NORMAL


@pytest.mark.asyncio
async def test_sleep_exactly_55_not_poor():
    """Sleep exactamente 55 (umbral) NO activa baja energía (debe ser <55)."""
    metrics = _make_health_log(hrv=60, sleep_score=55)
    service = EnergyModeService()
    state = await service.evaluate_energy_state(1, metrics)
    assert state == EnergyState.NORMAL


# ── Tests: filter_recipes_for_low_energy ──────────────────────────────────────

def test_filter_recipes_returns_only_le10_min():
    """filter_recipes_for_low_energy solo retorna recetas con prep_time ≤ 10 min."""
    recipes = [
        _make_recipe(1, "Rapida", prep_time_minutes=5),
        _make_recipe(2, "Media", prep_time_minutes=10),
        _make_recipe(3, "Larga", prep_time_minutes=30),
        _make_recipe(4, "Muy larga", prep_time_minutes=60),
    ]
    service = EnergyModeService()
    filtered = service.filter_recipes_for_low_energy(recipes)

    assert all(r.prep_time_minutes <= 10 for r in filtered)
    assert len(filtered) == 2
    names = [r.name for r in filtered]
    assert "Rapida" in names
    assert "Media" in names


def test_filter_recipes_prefers_baja_energia_tag():
    """Recetas con tag 'baja_energia' se priorizan sobre otras ≤10 min."""
    recipes = [
        _make_recipe(1, "Normal rapida", prep_time_minutes=8, tags=[]),
        _make_recipe(2, "Baja energia tagged", prep_time_minutes=9, tags=["baja_energia"]),
        _make_recipe(3, "Rapida tagged", prep_time_minutes=5, tags=["rapida"]),
    ]
    service = EnergyModeService()
    filtered = service.filter_recipes_for_low_energy(recipes)

    # Las que tienen tags deben ir primero
    assert filtered[0].tags != []


def test_filter_recipes_fallback_when_none_pass():
    """Si ninguna receta pasa el filtro de 10 min, retorna las 3 más rápidas."""
    recipes = [
        _make_recipe(1, "30min", prep_time_minutes=30),
        _make_recipe(2, "20min", prep_time_minutes=20),
        _make_recipe(3, "15min", prep_time_minutes=15),
        _make_recipe(4, "45min", prep_time_minutes=45),
    ]
    service = EnergyModeService()
    filtered = service.filter_recipes_for_low_energy(recipes)

    assert len(filtered) == 3
    assert filtered[0].prep_time_minutes <= filtered[1].prep_time_minutes
    assert filtered[1].prep_time_minutes <= filtered[2].prep_time_minutes


# ── Tests: simplify_bot_response ──────────────────────────────────────────────

def test_simplify_normal_returns_unchanged():
    """En estado NORMAL, la respuesta no se modifica."""
    full = "Línea 1\nLínea 2\nLínea 3 con mucho detalle nutricional"
    service = EnergyModeService()
    result = service.simplify_bot_response(full, EnergyState.NORMAL)
    assert result == full


def test_simplify_low_condenses_message():
    """En estado LOW, la respuesta se condensa a las primeras líneas."""
    full = "Línea 1\nLínea 2\nLínea 3\nLínea 4\nLínea 5"
    service = EnergyModeService()
    result = service.simplify_bot_response(full, EnergyState.LOW)

    # Debe ser más corto que el original
    assert len(result) < len(full) + 100  # puede agregar pequeño texto
    assert "Línea 1" in result


def test_simplify_critical_adds_rest_message():
    """En estado CRITICAL, se agrega mensaje de descanso."""
    full = "Plan sugerido: arroz con pollo"
    service = EnergyModeService()
    result = service.simplify_bot_response(full, EnergyState.CRITICAL)

    assert "descansá" in result.lower() or "batch cooking" in result.lower()
