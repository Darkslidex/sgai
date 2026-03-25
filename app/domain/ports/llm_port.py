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

    @abstractmethod
    async def parse_meal_description(
        self,
        description: str,
        ingredient_catalog: list[str],
    ) -> dict:
        """Parsea una descripción de comida en texto libre y retorna ítems estructurados.

        Args:
            description: Texto libre del usuario (ej. "almorcé 150g arroz y 200g pechuga").
            ingredient_catalog: Lista de nombres de ingredientes conocidos en la DB.

        Returns:
            dict con:
              - items: list de {ingredient, quantity_g, calories_kcal, protein_g}
              - meal_type_guess: str ('desayuno', 'almuerzo', 'cena', 'snack')
        """
        ...
