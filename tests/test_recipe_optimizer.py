"""Tests unitarios para RecipeOptimizer (sin DB — mocks de repositorios)."""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock

from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem
from app.domain.models.recipe import Recipe
from app.domain.models.recipe_ingredient import RecipeIngredient
from app.domain.services.recipe_optimizer import RecipeOptimizer


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_recipe(id: int, name: str, tags: list[str] | None = None) -> Recipe:
    return Recipe(
        id=id,
        name=name,
        description="",
        prep_time_minutes=30,
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


def _make_price(ingredient_id: int, price_ars: float, source: str = "seed") -> MarketPrice:
    return MarketPrice(
        id=ingredient_id,
        ingredient_id=ingredient_id,
        price_ars=price_ars,
        source=source,
        store=None,
        confidence=0.5,
        date=date(2026, 3, 1),
        created_at=datetime(2026, 3, 1),
    )


def _make_ri(id: int, recipe_id: int, ingredient_id: int, qty: float = 0.5) -> RecipeIngredient:
    return RecipeIngredient(
        id=id,
        recipe_id=recipe_id,
        ingredient_id=ingredient_id,
        quantity_amount=qty,
        unit="kg",
    )


def _make_pantry_item(ingredient_id: int, qty: float) -> PantryItem:
    return PantryItem(
        id=ingredient_id,
        user_id=1,
        ingredient_id=ingredient_id,
        quantity_amount=qty,
        unit="kg",
        expires_at=None,
        created_at=datetime(2026, 3, 1),
        updated_at=datetime(2026, 3, 1),
    )


def _make_optimizer(recipes, recipe_ingredients_map, prices) -> RecipeOptimizer:
    """Construye RecipeOptimizer con repositorios mockeados."""
    recipe_repo = AsyncMock()
    market_repo = AsyncMock()

    recipe_repo.list_recipes.return_value = recipes
    recipe_repo.get_recipe_ingredients.side_effect = lambda rid: recipe_ingredients_map.get(rid, [])
    market_repo.get_all_current_prices.return_value = prices

    return RecipeOptimizer(recipe_repo=recipe_repo, market_repo=market_repo)


# ── Tests: find_optimal_combination ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_optimal_combination_returns_ranked_results():
    """find_optimal_combination retorna hasta 3 resultados con overlap_score y cost."""
    recipes = [_make_recipe(i, f"Receta {i}") for i in range(1, 6)]

    # Recetas 1 y 2 comparten ingredientes 10 y 11; receta 3 no comparte nada
    ris = {
        1: [_make_ri(1, 1, 10), _make_ri(2, 1, 11)],
        2: [_make_ri(3, 2, 10), _make_ri(4, 2, 11)],
        3: [_make_ri(5, 3, 20), _make_ri(6, 3, 21)],
        4: [_make_ri(7, 4, 10), _make_ri(8, 4, 30)],
        5: [_make_ri(9, 5, 40), _make_ri(10, 5, 41)],
    }
    prices = [_make_price(i, 1000.0) for i in [10, 11, 20, 21, 30, 40, 41]]

    optimizer = _make_optimizer(recipes, ris, prices)
    results = await optimizer.find_optimal_combination(num_recipes=3)

    assert len(results) <= 3
    assert len(results) > 0
    for r in results:
        assert "recipes" in r
        assert "overlap_score" in r
        assert "estimated_cost_ars" in r
        assert "unique_ingredients" in r
        assert "shared_ingredients" in r
        assert len(r["recipes"]) == 3


@pytest.mark.asyncio
async def test_higher_overlap_scores_better():
    """Combinaciones con más solapamiento reciben mayor overlap_score."""
    r1 = _make_recipe(1, "Receta 1")
    r2 = _make_recipe(2, "Receta 2")
    r3 = _make_recipe(3, "Receta 3")

    # r1 + r2: comparten ings 10 y 11 (2 de 2 únicos = overlap 1.0)
    # r1 + r3: no comparten nada (0 de 4 = overlap 0.0)
    ris = {
        1: [_make_ri(1, 1, 10), _make_ri(2, 1, 11)],
        2: [_make_ri(3, 2, 10), _make_ri(4, 2, 11)],
        3: [_make_ri(5, 3, 20), _make_ri(6, 3, 21)],
    }
    prices = [_make_price(i, 1000.0) for i in [10, 11, 20, 21]]

    optimizer = _make_optimizer([r1, r2, r3], ris, prices)
    results = await optimizer.find_optimal_combination(num_recipes=2)

    assert len(results) > 0
    # El mejor resultado debe ser r1+r2 (overlap_score alto)
    best = results[0]
    assert best["overlap_score"] > 0.0


@pytest.mark.asyncio
async def test_max_budget_filters_expensive_combinations():
    """max_budget_ars filtra combinaciones que superan el presupuesto."""
    recipes = [_make_recipe(i, f"Receta {i}") for i in range(1, 4)]

    ris = {
        1: [_make_ri(1, 1, 10)],
        2: [_make_ri(2, 2, 20)],
        3: [_make_ri(3, 3, 30)],
    }
    # Cada ingrediente cuesta 10000 ARS
    prices = [_make_price(10, 10000.0), _make_price(20, 10000.0), _make_price(30, 10000.0)]

    optimizer = _make_optimizer(recipes, ris, prices)

    # Sin restricción de presupuesto: 1 combo de 3 recetas = 30000 ARS
    results_no_limit = await optimizer.find_optimal_combination(num_recipes=3)
    assert len(results_no_limit) == 1

    # Con presupuesto muy bajo: ninguna combo pasa
    results_limited = await optimizer.find_optimal_combination(
        num_recipes=3, max_budget_ars=5000.0
    )
    assert results_limited == []


@pytest.mark.asyncio
async def test_find_optimal_combination_fewer_recipes_than_requested():
    """Si hay menos recetas que num_recipes, ajusta num_recipes automáticamente."""
    recipes = [_make_recipe(1, "Única receta")]
    ris = {1: [_make_ri(1, 1, 10)]}
    prices = [_make_price(10, 1000.0)]

    optimizer = _make_optimizer(recipes, ris, prices)
    results = await optimizer.find_optimal_combination(num_recipes=3)

    # Debe retornar algo (con 1 receta, num_recipes se reduce a 1)
    assert len(results) >= 1
    assert len(results[0]["recipes"]) == 1


@pytest.mark.asyncio
async def test_find_optimal_combination_no_recipes_returns_empty():
    """Sin recetas disponibles retorna lista vacía."""
    optimizer = _make_optimizer([], {}, [])
    results = await optimizer.find_optimal_combination(num_recipes=3)
    assert results == []


# ── Tests: calculate_shopping_list ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calculate_shopping_list_empty_pantry():
    """Con pantry vacía, to_buy == needed para todos los ingredientes."""
    recipe_repo = AsyncMock()
    market_repo = AsyncMock()

    r1 = _make_recipe(1, "Arroz con pollo")
    r2 = _make_recipe(2, "Lentejas guisadas")

    recipe_repo.get_recipe_ingredients.side_effect = lambda rid: {
        1: [_make_ri(1, 1, 10, 0.5), _make_ri(2, 1, 20, 0.3)],
        2: [_make_ri(3, 2, 10, 0.2), _make_ri(4, 2, 30, 0.4)],
    }.get(rid, [])

    market_repo.get_all_current_prices.return_value = [
        _make_price(10, 5000.0),
        _make_price(20, 2000.0),
        _make_price(30, 2500.0),
    ]

    optimizer = RecipeOptimizer(recipe_repo=recipe_repo, market_repo=market_repo)
    shopping = await optimizer.calculate_shopping_list([r1, r2], pantry=[])

    assert len(shopping) > 0
    # Ingrediente 10 aparece en ambas recetas: 0.5 + 0.2 = 0.7
    ing10 = next(s for s in shopping if s["ingredient_id"] == 10)
    assert ing10["needed"] == pytest.approx(0.7, abs=0.001)
    assert ing10["to_buy"] == pytest.approx(0.7, abs=0.001)
    assert ing10["in_pantry"] == 0.0


@pytest.mark.asyncio
async def test_calculate_shopping_list_deducts_pantry():
    """Los items en pantry se descuentan de to_buy."""
    recipe_repo = AsyncMock()
    market_repo = AsyncMock()

    r1 = _make_recipe(1, "Pollo al horno")
    recipe_repo.get_recipe_ingredients.return_value = [
        _make_ri(1, 1, 10, 1.0),   # necesita 1 kg de ing 10
        _make_ri(2, 1, 20, 0.5),   # necesita 0.5 kg de ing 20
    ]
    market_repo.get_all_current_prices.return_value = [
        _make_price(10, 5000.0),
        _make_price(20, 3000.0),
    ]

    # Pantry tiene 0.4 kg de ing 10
    pantry = [_make_pantry_item(ingredient_id=10, qty=0.4)]

    optimizer = RecipeOptimizer(recipe_repo=recipe_repo, market_repo=market_repo)
    shopping = await optimizer.calculate_shopping_list([r1], pantry=pantry)

    ing10 = next(s for s in shopping if s["ingredient_id"] == 10)
    assert ing10["needed"] == pytest.approx(1.0, abs=0.001)
    assert ing10["in_pantry"] == pytest.approx(0.4, abs=0.001)
    assert ing10["to_buy"] == pytest.approx(0.6, abs=0.001)

    # Ing 20 no está en pantry
    ing20 = next(s for s in shopping if s["ingredient_id"] == 20)
    assert ing20["to_buy"] == pytest.approx(0.5, abs=0.001)


@pytest.mark.asyncio
async def test_calculate_shopping_list_pantry_covers_full_need():
    """Si pantry cubre toda la necesidad, to_buy == 0."""
    recipe_repo = AsyncMock()
    market_repo = AsyncMock()

    r1 = _make_recipe(1, "Ensalada")
    recipe_repo.get_recipe_ingredients.return_value = [
        _make_ri(1, 1, 10, 0.3),
    ]
    market_repo.get_all_current_prices.return_value = [_make_price(10, 2000.0)]

    # Pantry tiene más de lo necesario
    pantry = [_make_pantry_item(ingredient_id=10, qty=1.0)]

    optimizer = RecipeOptimizer(recipe_repo=recipe_repo, market_repo=market_repo)
    shopping = await optimizer.calculate_shopping_list([r1], pantry=pantry)

    ing10 = next(s for s in shopping if s["ingredient_id"] == 10)
    assert ing10["to_buy"] == 0.0
    assert ing10["estimated_cost_ars"] == 0.0


@pytest.mark.asyncio
async def test_calculate_shopping_list_sorted_by_cost_desc():
    """La lista de compras está ordenada por costo estimado descendente."""
    recipe_repo = AsyncMock()
    market_repo = AsyncMock()

    r1 = _make_recipe(1, "Receta cara")
    recipe_repo.get_recipe_ingredients.return_value = [
        _make_ri(1, 1, 10, 1.0),  # 1 kg × 8500 = 8500 ARS
        _make_ri(2, 1, 20, 1.0),  # 1 kg × 1000 = 1000 ARS
        _make_ri(3, 1, 30, 1.0),  # 1 kg × 5000 = 5000 ARS
    ]
    market_repo.get_all_current_prices.return_value = [
        _make_price(10, 8500.0),
        _make_price(20, 1000.0),
        _make_price(30, 5000.0),
    ]

    optimizer = RecipeOptimizer(recipe_repo=recipe_repo, market_repo=market_repo)
    shopping = await optimizer.calculate_shopping_list([r1], pantry=[])

    costs = [s["estimated_cost_ars"] for s in shopping]
    assert costs == sorted(costs, reverse=True)


@pytest.mark.asyncio
async def test_calculate_shopping_list_aggregates_across_recipes():
    """Los ingredientes compartidos entre recetas se suman correctamente."""
    recipe_repo = AsyncMock()
    market_repo = AsyncMock()

    r1 = _make_recipe(1, "Arroz salteado")
    r2 = _make_recipe(2, "Arroz con vegetales")

    recipe_repo.get_recipe_ingredients.side_effect = lambda rid: {
        1: [_make_ri(1, 1, 10, 0.3)],  # arroz 0.3 kg
        2: [_make_ri(2, 2, 10, 0.5)],  # arroz 0.5 kg
    }.get(rid, [])

    market_repo.get_all_current_prices.return_value = [_make_price(10, 1800.0)]

    optimizer = RecipeOptimizer(recipe_repo=recipe_repo, market_repo=market_repo)
    shopping = await optimizer.calculate_shopping_list([r1, r2], pantry=[])

    assert len(shopping) == 1
    ing10 = shopping[0]
    assert ing10["needed"] == pytest.approx(0.8, abs=0.001)
