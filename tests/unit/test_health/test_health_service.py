"""Tests unitarios para HealthService — TDEE dinámico con Harris-Benedict."""

import pytest
from datetime import date, datetime

from app.domain.models.health import HealthLog
from app.domain.models.user import UserProfile
from app.domain.services.health_service import HealthService, TDEEResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_profile(
    weight_kg: float = 80.0,
    height_cm: float = 178.0,
    age: int = 42,
    activity_level: str = "moderate",
    goal: str = "maintain",
) -> UserProfile:
    return UserProfile(
        id=1,
        telegram_chat_id="123456",
        name="Felix",
        age=age,
        weight_kg=weight_kg,
        height_cm=height_cm,
        activity_level=activity_level,
        goal=goal,
        max_storage_volume={"refrigerados": 50, "secos": 30, "congelados": 20},
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def _make_health_log(
    sleep_score: float | None = None,
    stress_level: float | None = None,
    hrv: float | None = None,
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


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_calculate_tdee_bmr_male_42_years():
    """BMR Harris-Benedict para hombre de 42 años, 80 kg, 178 cm."""
    profile = _make_profile(weight_kg=80.0, height_cm=178.0, age=42, activity_level="moderate", goal="maintain")
    service = HealthService()
    result = service.calculate_tdee(profile)

    # Harris-Benedict revisado: 88.362 + (13.397 × 80) + (4.799 × 178) - (5.677 × 42)
    expected_bmr = 88.362 + (13.397 * 80) + (4.799 * 178) - (5.677 * 42)
    assert result.bmr == pytest.approx(expected_bmr, abs=0.5)


def test_calculate_tdee_activity_sedentary():
    """Factor de actividad sedentario = 1.2."""
    profile = _make_profile(activity_level="sedentary", goal="maintain")
    result = HealthService().calculate_tdee(profile)
    assert result.activity_multiplier == 1.2
    expected = result.bmr * 1.2 * 1.0
    assert result.tdee == pytest.approx(int(round(expected)), abs=2)


def test_calculate_tdee_activity_light():
    """Factor de actividad ligero = 1.375."""
    profile = _make_profile(activity_level="light", goal="maintain")
    result = HealthService().calculate_tdee(profile)
    assert result.activity_multiplier == 1.375


def test_calculate_tdee_activity_active():
    """Factor de actividad activo = 1.725."""
    profile = _make_profile(activity_level="active", goal="maintain")
    result = HealthService().calculate_tdee(profile)
    assert result.activity_multiplier == 1.725


def test_calculate_tdee_activity_very_active():
    """Factor de actividad muy activo = 1.9."""
    profile = _make_profile(activity_level="very_active", goal="maintain")
    result = HealthService().calculate_tdee(profile)
    assert result.activity_multiplier == 1.9


def test_calculate_tdee_goal_lose():
    """Objetivo de pérdida aplica multiplicador 0.85."""
    profile = _make_profile(activity_level="moderate", goal="lose")
    result = HealthService().calculate_tdee(profile)
    assert result.goal_multiplier == 0.85


def test_calculate_tdee_goal_gain():
    """Objetivo de ganancia aplica multiplicador 1.15."""
    profile = _make_profile(activity_level="moderate", goal="gain")
    result = HealthService().calculate_tdee(profile)
    assert result.goal_multiplier == 1.15


def test_calculate_tdee_stress_high_reduces_5pct():
    """Estrés alto (>7) reduce TDEE en 5%."""
    profile = _make_profile(activity_level="moderate", goal="maintain")
    metrics_normal = _make_health_log(stress_level=5.0)
    metrics_stressed = _make_health_log(stress_level=8.0)

    service = HealthService()
    result_normal = service.calculate_tdee(profile, metrics_normal)
    result_stressed = service.calculate_tdee(profile, metrics_stressed)

    assert result_stressed.stress_adjustment == -0.05
    assert result_normal.stress_adjustment == 0.0
    # TDEE con estrés debe ser ~5% menor
    assert result_stressed.tdee < result_normal.tdee
    ratio = result_stressed.tdee / result_normal.tdee
    assert ratio == pytest.approx(0.95, abs=0.01)


def test_calculate_tdee_sleep_poor_reduces_5pct():
    """Sueño pobre (<60) reduce TDEE en 5%."""
    profile = _make_profile(activity_level="moderate", goal="maintain")
    metrics_good_sleep = _make_health_log(sleep_score=80.0)
    metrics_poor_sleep = _make_health_log(sleep_score=45.0)

    service = HealthService()
    result_good = service.calculate_tdee(profile, metrics_good_sleep)
    result_poor = service.calculate_tdee(profile, metrics_poor_sleep)

    assert result_poor.sleep_adjustment == -0.05
    assert result_good.sleep_adjustment == 0.0
    assert result_poor.tdee < result_good.tdee


def test_calculate_tdee_stress_and_sleep_max_10pct():
    """Estrés alto + sueño pobre → ajuste máximo -10% (no -15%)."""
    profile = _make_profile(activity_level="moderate", goal="maintain")
    metrics_both = _make_health_log(stress_level=9.0, sleep_score=40.0)
    metrics_none = _make_health_log(stress_level=3.0, sleep_score=80.0)

    service = HealthService()
    result_both = service.calculate_tdee(profile, metrics_both)
    result_none = service.calculate_tdee(profile, metrics_none)

    assert result_both.stress_adjustment == -0.05
    assert result_both.sleep_adjustment == -0.05
    # Total ajuste debe ser exactamente -10%
    total = result_both.stress_adjustment + result_both.sleep_adjustment
    assert max(total, -0.10) == -0.10  # capped at -10%

    ratio = result_both.tdee / result_none.tdee
    assert ratio == pytest.approx(0.90, abs=0.01)


def test_calculate_tdee_no_metrics_no_adjustment():
    """Sin métricas, no hay ajuste dinámico."""
    profile = _make_profile()
    result = HealthService().calculate_tdee(profile, None)
    assert result.stress_adjustment == 0.0
    assert result.sleep_adjustment == 0.0


def test_calculate_tdee_returns_tdee_result_type():
    """El retorno es siempre TDEEResult."""
    profile = _make_profile()
    result = HealthService().calculate_tdee(profile)
    assert isinstance(result, TDEEResult)
    assert isinstance(result.tdee, int)
    assert result.tdee > 0
    assert "final_tdee_kcal" in result.breakdown


def test_calculate_tdee_stress_exactly_7_no_adjustment():
    """Estrés exactamente 7.0 (umbral) NO activa ajuste (debe ser >7)."""
    profile = _make_profile()
    metrics = _make_health_log(stress_level=7.0)
    result = HealthService().calculate_tdee(profile, metrics)
    assert result.stress_adjustment == 0.0


def test_calculate_tdee_sleep_exactly_60_no_adjustment():
    """Sueño exactamente 60 (umbral) NO activa ajuste (debe ser <60)."""
    profile = _make_profile()
    metrics = _make_health_log(sleep_score=60.0)
    result = HealthService().calculate_tdee(profile, metrics)
    assert result.sleep_adjustment == 0.0
