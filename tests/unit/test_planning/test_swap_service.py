"""Tests unitarios del SwapService y Matriz de Eficiencia Nutricional (ADR-008)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models.ingredient import Ingredient
from app.domain.models.market import MarketPrice
from app.domain.services.swap_service import (
    SwapService,
    calculate_efficiency_score,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ing(id: int, name: str, category: str, protein: float | None, price_ars: float) -> tuple:
    ing = Ingredient(
        id=id, name=name, aliases=[], category=category,
        storage_type="refrigerado", unit="kg",
        protein_per_100g=protein, calories_per_100g=None,
        avg_shelf_life_days=7, created_at=datetime.now(),
    )
    price = MarketPrice(
        id=id, ingredient_id=id, price_ars=price_ars,
        source="manual", store=None, confidence=1.0,
        date=datetime.now().date(), created_at=datetime.now(),
    )
    return ing, price


def _make_swap_service(ingredients: list, prices: list) -> SwapService:
    ing_repo = AsyncMock()
    ing_repo.list_ingredients.return_value = ingredients
    ing_repo.get_ingredient.return_value = ingredients[0] if ingredients else None

    market_repo = AsyncMock()
    market_repo.get_all_current_prices.return_value = prices
    market_repo.get_current_price.return_value = prices[0] if prices else None

    return SwapService(ing_repo, market_repo)


# ── Tests del score ───────────────────────────────────────────────────────────

def test_efficiency_score_formula():
    """Verifica la fórmula: (protein/price) * 100."""
    ing, price = _ing(1, "pollo", "proteina", 27.0, 400.0)
    score = calculate_efficiency_score(ing, price)
    assert abs(score - 6.75) < 0.01  # 27/400 * 100 = 6.75


def test_efficiency_score_zero_protein():
    """Ingrediente sin proteína → score 0."""
    ing, price = _ing(1, "aceite", "grasa", None, 300.0)
    assert calculate_efficiency_score(ing, price) == 0.0


def test_efficiency_score_zero_price():
    """Precio 0 → score 0 (evitar división por cero)."""
    ing = Ingredient(
        id=1, name="test", aliases=[], category="proteina", storage_type="seco",
        unit="kg", protein_per_100g=10.0, calories_per_100g=None,
        avg_shelf_life_days=None, created_at=datetime.now(),
    )
    price = MagicMock()
    price.price_ars = 0.0
    assert calculate_efficiency_score(ing, price) == 0.0


def test_ranking_order_lentejas_huevo_pollo_carne():
    """ADR-008: lentejas > huevo > pollo > carne vacuna en efficiency_score."""
    # Precios y proteínas basados en Argentina (aprox)
    _, lentejas_price = _ing(1, "lentejas", "x", 9.0, 80.0)    # 11.25
    _, huevo_price = _ing(2, "huevo", "x", 13.0, 150.0)          # 8.67
    _, pollo_price = _ing(3, "pollo", "x", 27.0, 400.0)          # 6.75
    _, carne_price = _ing(4, "carne", "x", 26.0, 800.0)          # 3.25

    lentejas_ing = Ingredient(1, "lentejas", [], "proteina", "seco", "kg", 9.0, None, None, datetime.now())
    huevo_ing = Ingredient(2, "huevo", [], "proteina", "refrigerado", "unidad", 13.0, None, None, datetime.now())
    pollo_ing = Ingredient(3, "pollo", [], "proteina", "refrigerado", "kg", 27.0, None, None, datetime.now())
    carne_ing = Ingredient(4, "carne", [], "proteina", "refrigerado", "kg", 26.0, None, None, datetime.now())

    s_lentejas = calculate_efficiency_score(lentejas_ing, lentejas_price)
    s_huevo = calculate_efficiency_score(huevo_ing, huevo_price)
    s_pollo = calculate_efficiency_score(pollo_ing, pollo_price)
    s_carne = calculate_efficiency_score(carne_ing, carne_price)

    assert s_lentejas > s_huevo > s_pollo > s_carne


# ── Tests del SwapService ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suggest_swap_returns_top3():
    """suggest_swap retorna máximo 3 sustitutos."""
    original_ing, original_price = _ing(1, "pollo", "proteina", 27.0, 400.0)
    alt1_ing, alt1_price = _ing(2, "lentejas", "proteina", 9.0, 80.0)
    alt2_ing, alt2_price = _ing(3, "huevo", "proteina", 13.0, 150.0)
    alt3_ing, alt3_price = _ing(4, "cerdo", "proteina", 25.0, 350.0)
    alt4_ing, alt4_price = _ing(5, "atun", "proteina", 30.0, 500.0)

    ing_repo = AsyncMock()
    ing_repo.get_ingredient.return_value = original_ing
    ing_repo.list_ingredients.return_value = [original_ing, alt1_ing, alt2_ing, alt3_ing, alt4_ing]

    market_repo = AsyncMock()
    market_repo.get_current_price.return_value = original_price
    market_repo.get_all_current_prices.return_value = [
        original_price, alt1_price, alt2_price, alt3_price, alt4_price
    ]

    service = SwapService(ing_repo, market_repo)
    suggestions = await service.suggest_swap(1)

    assert len(suggestions) <= 3
    # El mejor score debe estar primero
    if len(suggestions) > 1:
        assert suggestions[0].efficiency_score >= suggestions[1].efficiency_score


@pytest.mark.asyncio
async def test_suggest_swap_excludes_original():
    """El original no aparece entre los sustitutos."""
    original_ing, original_price = _ing(1, "pollo", "proteina", 27.0, 400.0)
    alt_ing, alt_price = _ing(2, "lentejas", "proteina", 9.0, 80.0)

    ing_repo = AsyncMock()
    ing_repo.get_ingredient.return_value = original_ing
    ing_repo.list_ingredients.return_value = [original_ing, alt_ing]

    market_repo = AsyncMock()
    market_repo.get_current_price.return_value = original_price
    market_repo.get_all_current_prices.return_value = [original_price, alt_price]

    service = SwapService(ing_repo, market_repo)
    suggestions = await service.suggest_swap(1)

    ids = [s.ingredient.id for s in suggestions]
    assert 1 not in ids  # original excluido


@pytest.mark.asyncio
async def test_cost_delta_calculation():
    """cost_delta_ars refleja la diferencia real de precio."""
    original_ing, original_price = _ing(1, "carne", "proteina", 26.0, 800.0)
    cheaper_ing, cheaper_price = _ing(2, "pollo", "proteina", 27.0, 400.0)

    ing_repo = AsyncMock()
    ing_repo.get_ingredient.return_value = original_ing
    ing_repo.list_ingredients.return_value = [original_ing, cheaper_ing]

    market_repo = AsyncMock()
    market_repo.get_current_price.return_value = original_price
    market_repo.get_all_current_prices.return_value = [original_price, cheaper_price]

    service = SwapService(ing_repo, market_repo)
    suggestions = await service.suggest_swap(1)

    assert len(suggestions) == 1
    assert suggestions[0].cost_delta_ars == pytest.approx(400.0 - 800.0)  # -400 (más barato)


@pytest.mark.asyncio
async def test_protein_delta_calculation():
    """protein_delta_g refleja la diferencia de proteína."""
    original_ing, original_price = _ing(1, "lentejas", "proteina", 9.0, 80.0)
    higher_ing, higher_price = _ing(2, "pollo", "proteina", 27.0, 400.0)

    ing_repo = AsyncMock()
    ing_repo.get_ingredient.return_value = original_ing
    ing_repo.list_ingredients.return_value = [original_ing, higher_ing]

    market_repo = AsyncMock()
    market_repo.get_current_price.return_value = original_price
    market_repo.get_all_current_prices.return_value = [original_price, higher_price]

    service = SwapService(ing_repo, market_repo)
    suggestions = await service.suggest_swap(1)

    assert len(suggestions) == 1
    assert suggestions[0].protein_delta_g == pytest.approx(27.0 - 9.0)


@pytest.mark.asyncio
async def test_suggest_swap_no_same_category():
    """Si no hay candidatos de la misma categoría → lista vacía."""
    original_ing, original_price = _ing(1, "pollo", "proteina", 27.0, 400.0)
    diff_cat_ing, diff_cat_price = _ing(2, "arroz", "carbohidrato", 7.0, 100.0)

    ing_repo = AsyncMock()
    ing_repo.get_ingredient.return_value = original_ing
    ing_repo.list_ingredients.return_value = [original_ing, diff_cat_ing]

    market_repo = AsyncMock()
    market_repo.get_current_price.return_value = original_price
    market_repo.get_all_current_prices.return_value = [original_price, diff_cat_price]

    service = SwapService(ing_repo, market_repo)
    suggestions = await service.suggest_swap(1)

    assert suggestions == []


@pytest.mark.asyncio
async def test_efficiency_ranking_sorted_desc():
    """get_efficiency_ranking retorna ingredientes ordenados por score descendente."""
    ing1, p1 = _ing(1, "lentejas", "proteina", 9.0, 80.0)    # score ~11.25
    ing2, p2 = _ing(2, "pollo", "proteina", 27.0, 400.0)      # score ~6.75

    ing_repo = AsyncMock()
    ing_repo.list_ingredients.return_value = [ing1, ing2]

    market_repo = AsyncMock()
    market_repo.get_all_current_prices.return_value = [p1, p2]

    service = SwapService(ing_repo, market_repo)
    ranking = await service.get_efficiency_ranking()

    assert len(ranking) == 2
    assert ranking[0][0].name == "lentejas"
    assert ranking[0][1] > ranking[1][1]
