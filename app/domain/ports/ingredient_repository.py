"""Port (interfaz abstracta) del repositorio de ingredientes."""

from abc import ABC, abstractmethod

from app.domain.models.ingredient import Ingredient


class IngredientRepositoryPort(ABC):
    @abstractmethod
    async def create_ingredient(self, ingredient: Ingredient) -> Ingredient: ...

    @abstractmethod
    async def get_ingredient(self, ingredient_id: int) -> Ingredient | None: ...

    @abstractmethod
    async def list_ingredients(self) -> list[Ingredient]: ...

    @abstractmethod
    async def search_ingredients(self, query: str) -> list[Ingredient]: ...
