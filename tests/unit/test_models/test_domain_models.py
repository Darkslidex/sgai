"""Tests de dataclasses de dominio (sin dependencias ORM)."""

import json
from datetime import date, datetime

import pytest

from app.domain.models.health import HealthLog
from app.domain.models.ingredient import Ingredient
from app.domain.models.market import MarketPrice
from app.domain.models.optimization_log import OptimizationLog
from app.domain.models.pantry_item import PantryItem
from app.domain.models.planning import WeeklyPlan
from app.domain.models.recipe import Recipe
from app.domain.models.recipe_ingredient import RecipeIngredient
from app.domain.models.user import UserProfile
from app.domain.models.user_preference import UserPreference

NOW = datetime(2026, 3, 19, 12, 0, 0)
TODAY = date(2026, 3, 19)


def test_user_profile_creation():
    u = UserProfile(
        id=1,
        telegram_chat_id="6513721904",
        name="Felix",
        age=42,
        weight_kg=80.0,
        height_cm=175.0,
        activity_level="moderate",
        goal="maintain",
        max_storage_volume={"refrigerados": 50, "secos": 30, "congelados": 20},
        created_at=NOW,
        updated_at=NOW,
    )
    assert u.telegram_chat_id == "6513721904"
    assert u.age == 42


def test_user_profile_max_storage_volume_adr008():
    """ADR-008: max_storage_volume acepta y serializa dict de categorías."""
    storage = {"refrigerados": 50, "secos": 30, "congelados": 20}
    u = UserProfile(
        id=1,
        telegram_chat_id="123",
        name="Test",
        age=30,
        weight_kg=70.0,
        height_cm=170.0,
        activity_level="light",
        goal="lose",
        max_storage_volume=storage,
        created_at=NOW,
        updated_at=NOW,
    )
    assert u.max_storage_volume == storage
    assert u.max_storage_volume["refrigerados"] == 50
    # Serializable a JSON
    serialized = json.dumps(u.max_storage_volume)
    restored = json.loads(serialized)
    assert restored == storage


def test_health_log_creation():
    h = HealthLog(
        id=1,
        user_id=1,
        date=TODAY,
        sleep_score=85.0,
        stress_level=3.0,
        hrv=45.0,
        steps=8000,
        mood="good",
        notes="Buen día",
        source="manual",
        created_at=NOW,
    )
    assert h.sleep_score == 85.0
    assert h.mood == "good"


def test_health_log_nullable_fields():
    h = HealthLog(
        id=2,
        user_id=1,
        date=TODAY,
        sleep_score=None,
        stress_level=None,
        hrv=None,
        steps=None,
        mood=None,
        notes=None,
        source="health_connect",
        created_at=NOW,
    )
    assert h.sleep_score is None
    assert h.steps is None


def test_recipe_creation():
    r = Recipe(
        id=1,
        name="Arroz con pollo",
        description="Clásico argentino",
        prep_time_minutes=30,
        is_batch_friendly=True,
        reheatable_days=4,
        servings=5,
        calories_per_serving=450.0,
        protein_per_serving=35.0,
        carbs_per_serving=50.0,
        fat_per_serving=10.0,
        instructions=json.dumps([{"paso": 1, "texto": "Cocinar el arroz"}]),
        tags=["alta_proteina", "batch_cooking"],
        created_at=NOW,
    )
    assert r.is_batch_friendly is True
    assert "alta_proteina" in r.tags


def test_ingredient_creation():
    i = Ingredient(
        id=1,
        name="Pechuga de pollo",
        aliases=["pollo", "pechuga"],
        category="proteina",
        storage_type="refrigerado",
        unit="kg",
        protein_per_100g=23.0,
        calories_per_100g=165.0,
        avg_shelf_life_days=3,
        created_at=NOW,
    )
    assert "pollo" in i.aliases
    assert i.category == "proteina"


def test_market_price_creation():
    mp = MarketPrice(
        id=1,
        ingredient_id=1,
        price_ars=2500.0,
        source="manual",
        store="Coto",
        confidence=0.9,
        date=TODAY,
        created_at=NOW,
    )
    assert mp.price_ars == 2500.0
    assert mp.confidence == 0.9


def test_weekly_plan_creation():
    wp = WeeklyPlan(
        id=1,
        user_id=1,
        week_start=TODAY,
        plan_json={"lunes": ["arroz con pollo"]},
        shopping_list_json={"pollo": {"cantidad": 2, "precio": 5000}},
        total_cost_ars=15000.0,
        is_active=True,
        created_at=NOW,
        expires_at=datetime(2026, 3, 26, 12, 0, 0),
    )
    assert wp.is_active is True
    assert "lunes" in wp.plan_json


def test_user_preference_creation():
    p = UserPreference(
        id=1,
        user_id=1,
        key="sin_gluten",
        value="true",
        created_at=NOW,
    )
    assert p.key == "sin_gluten"


def test_recipe_ingredient_creation():
    ri = RecipeIngredient(
        id=1,
        recipe_id=1,
        ingredient_id=1,
        quantity_amount=0.5,
        unit="kg",
    )
    assert ri.quantity_amount == 0.5


def test_pantry_item_creation():
    pi = PantryItem(
        id=1,
        user_id=1,
        ingredient_id=1,
        quantity_amount=1.5,
        unit="kg",
        expires_at=datetime(2026, 3, 25, 0, 0, 0),
        created_at=NOW,
        updated_at=NOW,
    )
    assert pi.quantity_amount == 1.5
    assert pi.expires_at is not None


def test_pantry_item_no_expiry():
    pi = PantryItem(
        id=2,
        user_id=1,
        ingredient_id=2,
        quantity_amount=500.0,
        unit="g",
        expires_at=None,
        created_at=NOW,
        updated_at=NOW,
    )
    assert pi.expires_at is None


def test_optimization_log_creation():
    ol = OptimizationLog(
        id=1,
        user_id=1,
        week_start=TODAY,
        feedback="El plan estuvo bien, pero me sobraron proteínas",
        optimization_data={"score": 0.85, "adjustments": ["reduce_protein"]},
        created_at=NOW,
    )
    assert ol.optimization_data["score"] == 0.85
