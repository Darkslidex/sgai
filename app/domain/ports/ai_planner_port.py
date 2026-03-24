"""Port (interfaz abstracta) del planificador de IA."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.domain.models.ingredient import Ingredient
from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem
from app.domain.models.planning import WeeklyPlan
from app.domain.models.user import UserProfile
from app.domain.models.user_preference import UserPreference


@dataclass
class PlanningContext:
    """Toda la información necesaria para generar un plan semanal."""

    profile: UserProfile
    preferences: list[UserPreference]
    pantry: list[PantryItem]
    priced_ingredients: list[tuple[Ingredient, MarketPrice]]  # ingredientes con precio actual
    plan_history: list[WeeklyPlan]  # planes anteriores para evitar repetición
    tdee_kcal: int


@dataclass
class DayMeals:
    day: str    # "Lunes", "Martes", ...
    lunch: str  # nombre de la receta
    dinner: str


@dataclass
class ShoppingItem:
    ingredient_name: str
    quantity: float
    unit: str
    estimated_price_ars: float


@dataclass
class WeeklyPlanResult:
    days: list[DayMeals]
    shopping_list: list[ShoppingItem]
    total_cost_ars: float
    cooking_day: str
    prep_steps: list[str]
    tokens_used: int = 0


@dataclass
class SwapRequest:
    ingredient_id: int
    reason: str  # "unavailable", "too_expensive", "preference"
    user_id: int


@dataclass
class SwapSuggestion:
    ingredient: Ingredient
    current_price_ars: float
    protein_per_100g: float
    efficiency_score: float   # ADR-008: normalizado 0-100
    cost_delta_ars: float     # vs. ingrediente original
    protein_delta_g: float    # vs. ingrediente original
    reason: str


@dataclass
class SwapResult:
    original_ingredient_id: int
    suggestions: list[SwapSuggestion] = field(default_factory=list)


class AIPlannerPort(ABC):
    """Interfaz abstracta del planificador de IA. Intercambiable (DeepSeek, OpenAI, Ollama...)."""

    @abstractmethod
    async def generate_plan(self, context: PlanningContext) -> WeeklyPlanResult: ...

    @abstractmethod
    async def suggest_swap(self, request: SwapRequest) -> SwapResult: ...
