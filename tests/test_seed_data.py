"""Tests de integridad de los datos del seed (sin DB — solo Python puro)."""

import pytest

from scripts.seed_ingredients import INGREDIENTS
from scripts.seed_prices import PRICES
from scripts.seed_recipes import RECIPES

VALID_CATEGORIES = {"proteina", "verdura", "carbohidrato", "lacteo", "condimento", "grasa"}
VALID_STORAGE_TYPES = {"refrigerado", "seco", "congelado"}


def test_all_ingredients_have_valid_category():
    """Todos los ingredientes tienen una categoría válida."""
    invalid = [i["name"] for i in INGREDIENTS if i["category"] not in VALID_CATEGORIES]
    assert invalid == [], f"Categorías inválidas en: {invalid}"


def test_all_ingredients_have_valid_storage_type():
    """Todos los ingredientes tienen un storage_type válido."""
    invalid = [i["name"] for i in INGREDIENTS if i["storage_type"] not in VALID_STORAGE_TYPES]
    assert invalid == [], f"Storage types inválidos en: {invalid}"


def test_no_duplicate_ingredient_names():
    """No hay ingredientes con nombre duplicado."""
    names = [i["name"] for i in INGREDIENTS]
    duplicates = [n for n in names if names.count(n) > 1]
    assert duplicates == [], f"Ingredientes duplicados: {set(duplicates)}"


def test_at_least_60_ingredients():
    """Hay al menos 60 ingredientes en el seed."""
    assert len(INGREDIENTS) >= 60, f"Solo hay {len(INGREDIENTS)} ingredientes"


def test_all_ingredient_names_lowercase():
    """Los nombres canónicos están en minúsculas."""
    non_lower = [i["name"] for i in INGREDIENTS if i["name"] != i["name"].lower()]
    assert non_lower == [], f"Nombres no lowercase: {non_lower}"


def test_all_prices_reference_existing_ingredients():
    """Todos los precios referencian ingredientes existentes en el seed."""
    ingredient_names = {i["name"] for i in INGREDIENTS}
    orphan_prices = [
        p["ingredient_name"] for p in PRICES
        if p["ingredient_name"] not in ingredient_names
    ]
    assert orphan_prices == [], f"Precios sin ingrediente: {orphan_prices}"


def test_no_negative_prices():
    """No hay precios negativos o cero."""
    bad = [p["ingredient_name"] for p in PRICES if p["price_ars"] <= 0]
    assert bad == [], f"Precios <= 0: {bad}"


def test_prices_cover_all_ingredients():
    """Todos los ingredientes tienen al menos un precio seed."""
    priced = {p["ingredient_name"] for p in PRICES}
    ingredient_names = {i["name"] for i in INGREDIENTS}
    unpriced = ingredient_names - priced
    assert unpriced == set(), f"Ingredientes sin precio: {unpriced}"


def test_at_least_15_recipes():
    """Hay al menos 15 recetas en el seed."""
    assert len(RECIPES) >= 15, f"Solo hay {len(RECIPES)} recetas"


def test_all_recipes_are_batch_friendly():
    """Todas las recetas son is_batch_friendly=True."""
    non_batch = [r["name"] for r in RECIPES if not r["is_batch_friendly"]]
    assert non_batch == [], f"Recetas no batch-friendly: {non_batch}"


def test_all_recipes_have_reheatable_days_gte_3():
    """Todas las recetas tienen reheatable_days >= 3."""
    bad = [r["name"] for r in RECIPES if r["reheatable_days"] < 3]
    assert bad == [], f"Recetas con reheatable_days < 3: {bad}"


def test_all_recipes_use_known_ingredients():
    """Todas las recetas usan solo ingredientes definidos en el seed."""
    ingredient_names = {i["name"] for i in INGREDIENTS}
    errors = []
    for recipe in RECIPES:
        for ing in recipe["ingredients"]:
            if ing["name"] not in ingredient_names:
                errors.append(f"{recipe['name']} → {ing['name']}")
    assert errors == [], f"Ingredientes desconocidos en recetas: {errors}"


def test_no_duplicate_recipe_names():
    """No hay recetas con nombre duplicado."""
    names = [r["name"] for r in RECIPES]
    duplicates = [n for n in names if names.count(n) > 1]
    assert duplicates == [], f"Recetas duplicadas: {set(duplicates)}"


def test_at_least_3_recipes_with_legumes():
    """Al menos 3 recetas incluyen legumbres (lentejas, garbanzos, porotos)."""
    legumes = {"lentejas", "garbanzos", "porotos negros", "porotos blancos", "soja texturizada"}
    count = sum(
        1 for r in RECIPES
        if any(ing["name"] in legumes for ing in r["ingredients"])
    )
    assert count >= 3, f"Solo {count} recetas con legumbres"


def test_at_least_1_recipe_with_fish():
    """Al menos 1 receta incluye pescado (merluza, atun, salmon, sardinas)."""
    fish = {"merluza", "atun en lata", "salmon", "sardinas en lata"}
    count = sum(
        1 for r in RECIPES
        if any(ing["name"] in fish for ing in r["ingredients"])
    )
    assert count >= 1, f"No hay recetas con pescado"


def test_at_least_1_recipe_with_pork():
    """Al menos 1 receta con cerdo."""
    pork = {"cerdo bondiola"}
    count = sum(
        1 for r in RECIPES
        if any(ing["name"] in pork for ing in r["ingredients"])
    )
    assert count >= 1, "No hay recetas con cerdo"
