"""Tests de mappers dominio ↔ ORM (roundtrip)."""

import json
from datetime import date, datetime

import pytest

from app.adapters.persistence.mappers import (
    health_log_to_domain,
    health_log_to_orm,
    ingredient_to_domain,
    ingredient_to_orm,
    market_price_to_domain,
    market_price_to_orm,
    optimization_log_to_domain,
    optimization_log_to_orm,
    pantry_item_to_domain,
    pantry_item_to_orm,
    recipe_ingredient_to_domain,
    recipe_ingredient_to_orm,
    recipe_to_domain,
    recipe_to_orm,
    user_preference_to_domain,
    user_preference_to_orm,
    user_profile_to_domain,
    user_profile_to_orm,
    weekly_plan_to_domain,
    weekly_plan_to_orm,
)
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


def test_user_profile_roundtrip():
    domain = UserProfile(
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
    orm = user_profile_to_orm(domain)
    restored = user_profile_to_domain(orm)
    assert restored == domain


def test_user_profile_max_storage_volume_roundtrip():
    """ADR-008: max_storage_volume se preserva en el roundtrip dominio ↔ ORM."""
    storage = {"refrigerados": 80, "secos": 50, "congelados": 30, "ambiente": 10}
    domain = UserProfile(
        id=1,
        telegram_chat_id="111",
        name="Test",
        age=30,
        weight_kg=70.0,
        height_cm=170.0,
        activity_level="active",
        goal="gain",
        max_storage_volume=storage,
        created_at=NOW,
        updated_at=NOW,
    )
    orm = user_profile_to_orm(domain)
    assert orm.max_storage_volume == storage
    restored = user_profile_to_domain(orm)
    assert restored.max_storage_volume == storage


def test_health_log_roundtrip():
    domain = HealthLog(
        id=1,
        user_id=1,
        date=TODAY,
        sleep_score=85.0,
        stress_level=3.5,
        hrv=42.0,
        steps=7500,
        mood="good",
        notes="Sin novedades",
        source="manual",
        created_at=NOW,
    )
    orm = health_log_to_orm(domain)
    restored = health_log_to_domain(orm)
    assert restored == domain


def test_recipe_roundtrip():
    domain = Recipe(
        id=1,
        name="Milanesa napolitana",
        description="Clásico porteño",
        prep_time_minutes=25,
        is_batch_friendly=True,
        reheatable_days=3,
        servings=4,
        calories_per_serving=520.0,
        protein_per_serving=38.0,
        carbs_per_serving=30.0,
        fat_per_serving=18.0,
        instructions=json.dumps([{"paso": 1, "texto": "Empanar la carne"}]),
        tags=["alta_proteina", "batch_cooking"],
        created_at=NOW,
    )
    orm = recipe_to_orm(domain)
    restored = recipe_to_domain(orm)
    assert restored == domain


def test_ingredient_roundtrip():
    domain = Ingredient(
        id=1,
        name="Arroz",
        aliases=["arroz blanco", "arroz largo fino"],
        category="carbohidrato",
        storage_type="seco",
        unit="kg",
        protein_per_100g=7.0,
        calories_per_100g=365.0,
        avg_shelf_life_days=365,
        created_at=NOW,
    )
    orm = ingredient_to_orm(domain)
    restored = ingredient_to_domain(orm)
    assert restored == domain


def test_market_price_roundtrip():
    domain = MarketPrice(
        id=1,
        ingredient_id=1,
        price_ars=800.0,
        source="manual",
        store="Carrefour",
        confidence=0.95,
        date=TODAY,
        created_at=NOW,
    )
    orm = market_price_to_orm(domain)
    restored = market_price_to_domain(orm)
    assert restored == domain


def test_weekly_plan_roundtrip():
    domain = WeeklyPlan(
        id=1,
        user_id=1,
        week_start=TODAY,
        plan_json={"lunes": ["milanesa"], "martes": ["arroz con pollo"]},
        shopping_list_json={"arroz": {"kg": 2, "ars": 1600}},
        total_cost_ars=18000.0,
        is_active=True,
        created_at=NOW,
        expires_at=datetime(2026, 3, 26, 12, 0, 0),
    )
    orm = weekly_plan_to_orm(domain)
    restored = weekly_plan_to_domain(orm)
    assert restored == domain


def test_user_preference_roundtrip():
    domain = UserPreference(
        id=1,
        user_id=1,
        key="vegetariano",
        value="false",
        created_at=NOW,
    )
    orm = user_preference_to_orm(domain)
    restored = user_preference_to_domain(orm)
    assert restored == domain


def test_recipe_ingredient_roundtrip():
    domain = RecipeIngredient(
        id=1,
        recipe_id=1,
        ingredient_id=2,
        quantity_amount=0.3,
        unit="kg",
    )
    orm = recipe_ingredient_to_orm(domain)
    restored = recipe_ingredient_to_domain(orm)
    assert restored == domain


def test_pantry_item_roundtrip():
    domain = PantryItem(
        id=1,
        user_id=1,
        ingredient_id=3,
        quantity_amount=2.0,
        unit="litro",
        expires_at=datetime(2026, 3, 22, 0, 0, 0),
        created_at=NOW,
        updated_at=NOW,
    )
    orm = pantry_item_to_orm(domain)
    restored = pantry_item_to_domain(orm)
    assert restored == domain


def test_optimization_log_roundtrip():
    domain = OptimizationLog(
        id=1,
        user_id=1,
        week_start=TODAY,
        feedback="Buen plan, ajustar porciones",
        optimization_data={"score": 0.9, "iterations": 3},
        created_at=NOW,
    )
    orm = optimization_log_to_orm(domain)
    restored = optimization_log_to_domain(orm)
    assert restored == domain
