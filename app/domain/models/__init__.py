"""Modelos de dominio (dataclasses). Sin dependencias de SQLAlchemy u ORM externo."""

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

__all__ = [
    "UserProfile",
    "HealthLog",
    "Recipe",
    "Ingredient",
    "MarketPrice",
    "WeeklyPlan",
    "UserPreference",
    "RecipeIngredient",
    "PantryItem",
    "OptimizationLog",
]
