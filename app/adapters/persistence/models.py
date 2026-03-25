"""Modelos ORM de SQLAlchemy.

Importar aquí todos los modelos para que Alembic los detecte en autogenerate.
"""

from app.database import Base  # noqa: F401 — re-export para alembic

from app.adapters.persistence.user_profile_orm import UserProfileORM  # noqa: F401
from app.adapters.persistence.health_log_orm import HealthLogORM  # noqa: F401
from app.adapters.persistence.recipe_orm import RecipeORM  # noqa: F401
from app.adapters.persistence.ingredient_orm import IngredientORM  # noqa: F401
from app.adapters.persistence.market_price_orm import MarketPriceORM  # noqa: F401
from app.adapters.persistence.weekly_plan_orm import WeeklyPlanORM  # noqa: F401
from app.adapters.persistence.user_preference_orm import UserPreferenceORM  # noqa: F401
from app.adapters.persistence.recipe_ingredient_orm import RecipeIngredientORM  # noqa: F401
from app.adapters.persistence.pantry_item_orm import PantryItemORM  # noqa: F401
from app.adapters.persistence.optimization_log_orm import OptimizationLogORM  # noqa: F401
from app.adapters.persistence.meal_log_orm import MealLogORM  # noqa: F401
