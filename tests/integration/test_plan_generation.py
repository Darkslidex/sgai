"""Tests de integración: generación de plan con mock de DeepSeek API."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.models.ingredient import Ingredient
from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem
from app.domain.models.planning import WeeklyPlan
from app.domain.models.user import UserProfile
from app.domain.models.user_preference import UserPreference
from app.domain.ports.ai_planner_port import PlanningContext
from app.adapters.ai.deepseek_adapter import DeepSeekAdapter


# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_PLAN_JSON = {
    "days": [
        {"day": "Lunes", "lunch": "Pollo al limón", "dinner": "Arroz con verduras"},
        {"day": "Martes", "lunch": "Lentejas guisadas", "dinner": "Pollo al limón"},
        {"day": "Miércoles", "lunch": "Arroz con pollo", "dinner": "Lentejas guisadas"},
        {"day": "Jueves", "lunch": "Pollo al limón", "dinner": "Arroz con verduras"},
        {"day": "Viernes", "lunch": "Lentejas guisadas", "dinner": "Pollo al limón"},
    ],
    "shopping_list": [
        {"ingredient_name": "pollo", "quantity": 2.5, "unit": "kg", "estimated_price_ars": 2500.0},
        {"ingredient_name": "arroz", "quantity": 1.0, "unit": "kg", "estimated_price_ars": 400.0},
        {"ingredient_name": "lentejas", "quantity": 0.5, "unit": "kg", "estimated_price_ars": 300.0},
    ],
    "total_cost_ars": 14500.0,
    "cooking_day": "Domingo",
    "prep_steps": [
        "1. Cocinar arroz integral (30 min)",
        "2. Preparar lentejas guisadas (45 min)",
        "3. Marinar y hornear pollo (45 min)",
    ],
}


def _make_profile() -> UserProfile:
    return UserProfile(
        id=1, telegram_chat_id="6513721904", name="Felix",
        age=42, weight_kg=80.0, height_cm=175.0,
        activity_level="moderate", goal="maintain",
        max_storage_volume={"refrigerados": 50, "secos": 30, "congelados": 20},
        created_at=datetime.now(), updated_at=datetime.now(),
    )


def _make_context() -> PlanningContext:
    profile = _make_profile()
    ing = Ingredient(
        id=1, name="pollo", aliases=[], category="proteina",
        storage_type="refrigerado", unit="kg",
        protein_per_100g=27.0, calories_per_100g=165.0,
        avg_shelf_life_days=5, created_at=datetime.now(),
    )
    price = MarketPrice(
        id=1, ingredient_id=1, price_ars=400.0,
        source="manual", store=None, confidence=1.0,
        date=datetime.now().date(), created_at=datetime.now(),
    )
    return PlanningContext(
        profile=profile,
        preferences=[],
        pantry=[],
        priced_ingredients=[(ing, price)],
        plan_history=[],
        tdee_kcal=2400,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_plan_generation_with_mock_deepseek():
    """El adapter parsea correctamente una respuesta válida de DeepSeek."""
    adapter = DeepSeekAdapter(api_key="test", base_url="https://api.deepseek.com/v1")
    context = _make_context()

    mock_response = {
        "choices": [{"message": {"content": json.dumps(VALID_PLAN_JSON)}}],
        "usage": {"total_tokens": 850},
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await adapter.generate_plan(context)

    assert len(result.days) == 5
    assert result.days[0].day == "Lunes"
    assert result.days[0].lunch == "Pollo al limón"
    assert result.total_cost_ars == 14500.0
    assert result.cooking_day == "Domingo"
    assert len(result.prep_steps) == 3
    assert result.tokens_used == 850


@pytest.mark.asyncio
async def test_plan_shopping_list_parsed():
    """La lista de compras se parsea correctamente."""
    adapter = DeepSeekAdapter(api_key="test", base_url="https://api.deepseek.com/v1")
    context = _make_context()

    mock_response = {
        "choices": [{"message": {"content": json.dumps(VALID_PLAN_JSON)}}],
        "usage": {"total_tokens": 500},
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response_obj
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await adapter.generate_plan(context)

    assert len(result.shopping_list) == 3
    pollo = next(i for i in result.shopping_list if i.ingredient_name == "pollo")
    assert pollo.quantity == 2.5
    assert pollo.unit == "kg"
    assert pollo.estimated_price_ars == 2500.0


@pytest.mark.asyncio
async def test_retry_on_invalid_json():
    """Si el LLM devuelve JSON inválido, el adapter reintenta con contexto de error."""
    adapter = DeepSeekAdapter(api_key="test", base_url="https://api.deepseek.com/v1")
    context = _make_context()

    invalid_response = {
        "choices": [{"message": {"content": "esto no es JSON"}}],
        "usage": {"total_tokens": 10},
    }
    valid_response = {
        "choices": [{"message": {"content": json.dumps(VALID_PLAN_JSON)}}],
        "usage": {"total_tokens": 850},
    }

    call_count = 0

    async def fake_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = invalid_response if call_count == 1 else valid_response
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = fake_post
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await adapter.generate_plan(context)

    assert call_count == 2  # Un intento inválido + uno válido
    assert len(result.days) == 5


@pytest.mark.asyncio
async def test_raises_after_two_invalid_responses():
    """Si el LLM falla dos veces con JSON inválido → ValueError."""
    adapter = DeepSeekAdapter(api_key="test", base_url="https://api.deepseek.com/v1")
    context = _make_context()

    invalid_response = {
        "choices": [{"message": {"content": "no es JSON"}}],
        "usage": {"total_tokens": 5},
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = invalid_response
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(ValueError, match="JSON inválido"):
            await adapter.generate_plan(context)
