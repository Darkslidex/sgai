"""Tests del ConsumptionRatioService: ratio consumo/vencimiento (ADR-008)."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.domain.models.ingredient import Ingredient
from app.domain.models.pantry_item import PantryItem
from app.domain.models.planning import WeeklyPlan
from app.domain.services.consumption_ratio_service import (
    ConsumptionRatioService,
    WasteRiskItem,
)


def _make_ingredient(id=1, name="pollo", unit="kg", shelf_life=7):
    return Ingredient(
        id=id, name=name, aliases=[], category="proteina",
        storage_type="refrigerado", unit=unit,
        protein_per_100g=20.0, calories_per_100g=165.0,
        avg_shelf_life_days=shelf_life, created_at=datetime.utcnow(),
    )


def _make_pantry_item(ingredient_id=1, quantity=2.0, unit="kg", expires_at=None):
    return PantryItem(
        id=1, user_id=1, ingredient_id=ingredient_id,
        quantity_amount=quantity, unit=unit,
        expires_at=expires_at, created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


def _make_plan(week_start, items: list[dict]) -> WeeklyPlan:
    return WeeklyPlan(
        id=1, user_id=1, week_start=week_start,
        plan_json={"days": []},
        shopping_list_json={"items": items},
        total_cost_ars=5000.0, is_active=True,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )


@pytest.fixture
def mock_market_repo():
    repo = MagicMock()
    repo.get_pantry = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_planning_repo():
    repo = MagicMock()
    repo.get_plan_history = AsyncMock(return_value=[])
    repo.get_active_plan = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_ingredient_repo():
    repo = MagicMock()
    repo.get_ingredient = AsyncMock(return_value=_make_ingredient())
    return repo


@pytest.fixture
def service(mock_market_repo, mock_planning_repo, mock_ingredient_repo):
    return ConsumptionRatioService(mock_market_repo, mock_planning_repo, mock_ingredient_repo)


# ── calculate_consumption_rate ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consumption_rate_with_4_weeks_history(service, mock_planning_repo, mock_ingredient_repo):
    """Con 4 semanas de datos, retorna confidence proporcional a 4/8."""
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="pollo")
    plans = [
        _make_plan(date.today() - timedelta(weeks=i),
                   [{"ingredient_name": "pollo", "quantity": 0.5, "unit": "kg"}])
        for i in range(4)
    ]
    mock_planning_repo.get_plan_history.return_value = plans

    rate = await service.calculate_consumption_rate(user_id=1, ingredient_id=1)

    assert rate.avg_weekly_consumption == pytest.approx(0.5, rel=0.01)
    assert rate.data_points == 4
    assert rate.confidence == pytest.approx(0.5, rel=0.01)  # 4/8
    assert rate.source == "historical"


@pytest.mark.asyncio
async def test_consumption_rate_with_8_weeks_has_full_confidence(service, mock_planning_repo, mock_ingredient_repo):
    """Con 8 semanas de datos, confidence debe ser 1.0."""
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="arroz")
    plans = [
        _make_plan(date.today() - timedelta(weeks=i),
                   [{"ingredient_name": "arroz", "quantity": 1.0, "unit": "kg"}])
        for i in range(8)
    ]
    mock_planning_repo.get_plan_history.return_value = plans

    rate = await service.calculate_consumption_rate(user_id=1, ingredient_id=1)

    assert rate.confidence == pytest.approx(1.0, rel=0.01)
    assert rate.data_points == 8


@pytest.mark.asyncio
async def test_consumption_rate_with_1_week_uses_estimated(service, mock_planning_repo, mock_ingredient_repo):
    """Con solo 1 semana de historial, usa estimado del plan activo."""
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="pollo")
    # Solo 1 plan en historial (< MIN_DATA_POINTS=2)
    plans = [_make_plan(date.today() - timedelta(weeks=1),
                        [{"ingredient_name": "pollo", "quantity": 0.5, "unit": "kg"}])]
    mock_planning_repo.get_plan_history.return_value = plans

    # Simular plan activo
    active = _make_plan(date.today(), [{"ingredient_name": "pollo", "quantity": 0.6, "unit": "kg"}])
    mock_planning_repo.get_active_plan.return_value = active

    rate = await service.calculate_consumption_rate(user_id=1, ingredient_id=1)

    assert rate.source == "estimated"
    assert rate.data_points <= 1


@pytest.mark.asyncio
async def test_consumption_rate_returns_zero_for_unknown_ingredient(service, mock_ingredient_repo):
    """Retorna rate=0 si el ingrediente no existe."""
    mock_ingredient_repo.get_ingredient.return_value = None

    rate = await service.calculate_consumption_rate(user_id=1, ingredient_id=999)

    assert rate.avg_weekly_consumption == 0.0
    assert rate.data_points == 0
    assert rate.confidence == 0.0


# ── validate_purchase_suggestion ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_excessive_quantity_returns_invalid(service, mock_planning_repo, mock_ingredient_repo):
    """Cantidad que supera la vida útil debe retornar is_valid=False con cantidad ajustada."""
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="pollo")
    # Consumo: 0.5 kg/semana = 0.071 kg/día → 2kg tarda ~28 días en consumirse
    plans = [
        _make_plan(date.today() - timedelta(weeks=i),
                   [{"ingredient_name": "pollo", "quantity": 0.5, "unit": "kg"}])
        for i in range(4)
    ]
    mock_planning_repo.get_plan_history.return_value = plans

    validation = await service.validate_purchase_suggestion(
        user_id=1,
        ingredient_id=1,
        suggested_quantity=2.0,  # 2 kg
        shelf_life_days=5,        # solo 5 días de vida útil
    )

    assert validation.is_valid is False
    assert validation.suggested_quantity_adjusted is not None
    assert validation.suggested_quantity_adjusted < 2.0
    assert validation.waste_risk_percentage > 0


@pytest.mark.asyncio
async def test_validate_adequate_quantity_returns_valid(service, mock_planning_repo, mock_ingredient_repo):
    """Cantidad que puede consumirse antes del vencimiento → is_valid=True."""
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="pollo")
    # Consumo: 1.0 kg/semana = 0.14 kg/día → 0.5 kg tarda ~3.5 días
    plans = [
        _make_plan(date.today() - timedelta(weeks=i),
                   [{"ingredient_name": "pollo", "quantity": 1.0, "unit": "kg"}])
        for i in range(4)
    ]
    mock_planning_repo.get_plan_history.return_value = plans

    validation = await service.validate_purchase_suggestion(
        user_id=1,
        ingredient_id=1,
        suggested_quantity=0.5,   # 500g
        shelf_life_days=7,         # 7 días de vida útil
    )

    assert validation.is_valid is True
    assert validation.suggested_quantity_adjusted is None
    assert validation.waste_risk_percentage == 0.0


@pytest.mark.asyncio
async def test_validate_without_consumption_history_returns_valid(service, mock_planning_repo, mock_ingredient_repo):
    """Sin historial de consumo, se considera la cantidad válida (no se puede validar)."""
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="nuevo_ingrediente")
    mock_planning_repo.get_plan_history.return_value = []
    mock_planning_repo.get_active_plan.return_value = None

    validation = await service.validate_purchase_suggestion(
        user_id=1, ingredient_id=1, suggested_quantity=1.0, shelf_life_days=7
    )

    assert validation.is_valid is True


# ── get_waste_risk_report ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_waste_risk_report_identifies_at_risk_items(service, mock_market_repo, mock_planning_repo, mock_ingredient_repo):
    """waste_risk_report clasifica correctamente los items en riesgo."""
    # Item que vence en 3 días pero tardará 10 días en consumirse
    expires_soon = datetime.utcnow() + timedelta(days=3)
    at_risk_item = _make_pantry_item(ingredient_id=1, quantity=1.0, expires_at=expires_soon)
    mock_market_repo.get_pantry.return_value = [at_risk_item]

    # Consumo lento: 0.1 kg/semana
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="pollo")
    plans = [
        _make_plan(date.today() - timedelta(weeks=i),
                   [{"ingredient_name": "pollo", "quantity": 0.1, "unit": "kg"}])
        for i in range(4)
    ]
    mock_planning_repo.get_plan_history.return_value = plans

    report = await service.get_waste_risk_report(user_id=1)

    assert len(report) == 1
    assert report[0].action in ("will_waste", "consume_soon")
    assert report[0].waste_risk > 0


@pytest.mark.asyncio
async def test_waste_risk_report_ok_for_fast_consumption(service, mock_market_repo, mock_planning_repo, mock_ingredient_repo):
    """Items con consumo rápido deben clasificarse como 'ok'."""
    expires_in_week = datetime.utcnow() + timedelta(days=7)
    item = _make_pantry_item(ingredient_id=1, quantity=0.2, expires_at=expires_in_week)
    mock_market_repo.get_pantry.return_value = [item]

    # Consumo rápido: 2.0 kg/semana → 0.2 kg en ~0.7 días
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="pollo")
    plans = [
        _make_plan(date.today() - timedelta(weeks=i),
                   [{"ingredient_name": "pollo", "quantity": 2.0, "unit": "kg"}])
        for i in range(4)
    ]
    mock_planning_repo.get_plan_history.return_value = plans

    report = await service.get_waste_risk_report(user_id=1)

    assert len(report) == 1
    assert report[0].action == "ok"
    assert report[0].waste_risk == 0.0


@pytest.mark.asyncio
async def test_waste_risk_report_empty_pantry(service, mock_market_repo):
    """Reporte vacío si el pantry está vacío."""
    mock_market_repo.get_pantry.return_value = []

    report = await service.get_waste_risk_report(user_id=1)

    assert report == []


# ── Integración: shopping list ajustada por ratio ────────────────────────────

@pytest.mark.asyncio
async def test_validate_purchase_adjusted_message_contains_ingredient_name(
    service, mock_planning_repo, mock_ingredient_repo
):
    """El mensaje de validación debe incluir el nombre del ingrediente."""
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(name="pollo")
    plans = [
        _make_plan(date.today() - timedelta(weeks=i),
                   [{"ingredient_name": "pollo", "quantity": 0.3, "unit": "kg"}])
        for i in range(4)
    ]
    mock_planning_repo.get_plan_history.return_value = plans

    validation = await service.validate_purchase_suggestion(
        user_id=1, ingredient_id=1, suggested_quantity=5.0, shelf_life_days=3
    )

    assert "pollo" in validation.message.lower()
    assert validation.is_valid is False
