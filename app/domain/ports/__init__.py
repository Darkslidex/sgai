"""Interfaces abstractas (ABC) que definen los contratos entre dominio y adaptadores."""

from app.domain.ports.health_data_port import HealthDataPort
from app.domain.ports.health_repository import HealthRepositoryPort
from app.domain.ports.ingredient_repository import IngredientRepositoryPort
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.market_repository import MarketRepositoryPort
from app.domain.ports.planning_repository import PlanningRepositoryPort
from app.domain.ports.recipe_repository import RecipeRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort

__all__ = [
    "UserRepositoryPort",
    "HealthRepositoryPort",
    "RecipeRepositoryPort",
    "IngredientRepositoryPort",
    "MarketRepositoryPort",
    "PlanningRepositoryPort",
    "LLMPort",
    "HealthDataPort",
]
