"""Port (interfaz abstracta) del repositorio de recetas."""

from abc import ABC, abstractmethod

from app.domain.models.recipe import Recipe
from app.domain.models.recipe_ingredient import RecipeIngredient


class RecipeRepositoryPort(ABC):
    @abstractmethod
    async def create_recipe(self, recipe: Recipe, ingredients: list[RecipeIngredient]) -> Recipe: ...

    @abstractmethod
    async def get_recipe(self, recipe_id: int) -> Recipe | None: ...

    @abstractmethod
    async def list_recipes(self, filters: dict | None = None) -> list[Recipe]: ...

    @abstractmethod
    async def get_overlapping_recipes(
        self, ingredient_ids: list[int], min_overlap: int = 2
    ) -> list[Recipe]: ...

    @abstractmethod
    async def get_recipe_ingredients(self, recipe_id: int) -> list[RecipeIngredient]: ...
