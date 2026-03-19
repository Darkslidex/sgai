"""Mappers dominio ↔ ORM. Conversión entre dataclasses de dominio y modelos SQLAlchemy."""

from app.adapters.persistence.mappers.health_log_mapper import health_log_to_domain, health_log_to_orm
from app.adapters.persistence.mappers.ingredient_mapper import ingredient_to_domain, ingredient_to_orm
from app.adapters.persistence.mappers.market_price_mapper import market_price_to_domain, market_price_to_orm
from app.adapters.persistence.mappers.optimization_log_mapper import (
    optimization_log_to_domain,
    optimization_log_to_orm,
)
from app.adapters.persistence.mappers.pantry_item_mapper import pantry_item_to_domain, pantry_item_to_orm
from app.adapters.persistence.mappers.planning_mapper import weekly_plan_to_domain, weekly_plan_to_orm
from app.adapters.persistence.mappers.recipe_ingredient_mapper import (
    recipe_ingredient_to_domain,
    recipe_ingredient_to_orm,
)
from app.adapters.persistence.mappers.recipe_mapper import recipe_to_domain, recipe_to_orm
from app.adapters.persistence.mappers.user_preference_mapper import (
    user_preference_to_domain,
    user_preference_to_orm,
)
from app.adapters.persistence.mappers.user_profile_mapper import user_profile_to_domain, user_profile_to_orm

__all__ = [
    "user_profile_to_domain",
    "user_profile_to_orm",
    "health_log_to_domain",
    "health_log_to_orm",
    "recipe_to_domain",
    "recipe_to_orm",
    "ingredient_to_domain",
    "ingredient_to_orm",
    "market_price_to_domain",
    "market_price_to_orm",
    "weekly_plan_to_domain",
    "weekly_plan_to_orm",
    "user_preference_to_domain",
    "user_preference_to_orm",
    "recipe_ingredient_to_domain",
    "recipe_ingredient_to_orm",
    "pantry_item_to_domain",
    "pantry_item_to_orm",
    "optimization_log_to_domain",
    "optimization_log_to_orm",
]
