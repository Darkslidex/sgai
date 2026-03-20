"""Port abstracto para adaptadores de precios de mercado (3 niveles ADR-004)."""

from abc import ABC, abstractmethod

from app.domain.models.market import MarketPrice


class MarketPricePort(ABC):
    """Interfaz común para los tres adaptadores de precios (Manual / SEPA / Scraping)."""

    @abstractmethod
    async def get_price(self, ingredient_id: int) -> MarketPrice | None:
        """Retorna el precio más reciente para un ingrediente, o None si no disponible."""
        ...

    @abstractmethod
    async def save_price(
        self,
        ingredient_id: int,
        price_ars: float,
        store: str | None = None,
    ) -> MarketPrice:
        """Persiste un nuevo precio en la fuente correspondiente."""
        ...
