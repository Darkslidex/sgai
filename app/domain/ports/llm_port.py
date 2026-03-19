"""Port (interfaz abstracta) del motor de IA/LLM."""

from abc import ABC, abstractmethod


class LLMPort(ABC):
    """Interfaz abstracta para el motor de IA. Permite cambiar de DeepSeek a otro LLM."""

    @abstractmethod
    async def generate_weekly_plan(self, context: dict) -> dict: ...

    @abstractmethod
    async def suggest_quick_swap(
        self,
        original_ingredient: str,
        available_alternatives: list[str],
        recipe_context: dict,
    ) -> dict: ...

    @abstractmethod
    async def analyze_mood_food(self, health_data: list[dict], meal_data: list[dict]) -> dict: ...
