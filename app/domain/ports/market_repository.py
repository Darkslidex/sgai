"""Port (interfaz abstracta) del repositorio de mercado y despensa."""

from abc import ABC, abstractmethod

from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem


class MarketRepositoryPort(ABC):
    @abstractmethod
    async def add_price(self, price: MarketPrice) -> MarketPrice: ...

    @abstractmethod
    async def get_current_price(self, ingredient_id: int) -> MarketPrice | None: ...

    @abstractmethod
    async def get_price_history(self, ingredient_id: int, days: int = 30) -> list[MarketPrice]: ...

    @abstractmethod
    async def get_all_current_prices(self) -> list[MarketPrice]: ...

    @abstractmethod
    async def get_prices_by_source(
        self, ingredient_id: int, source: str, days: int = 30
    ) -> list[MarketPrice]: ...

    @abstractmethod
    async def get_pantry(self, user_id: int) -> list[PantryItem]: ...

    @abstractmethod
    async def update_pantry(self, item: PantryItem) -> PantryItem: ...

    @abstractmethod
    async def get_pantry_item(self, user_id: int, ingredient_id: int) -> PantryItem | None: ...

    @abstractmethod
    async def delete_pantry_item(self, user_id: int, ingredient_id: int) -> None: ...

    @abstractmethod
    async def get_expiring_pantry(self, user_id: int, days: int) -> list[PantryItem]: ...

    @abstractmethod
    async def get_expired_pantry(self, user_id: int) -> list[PantryItem]: ...
