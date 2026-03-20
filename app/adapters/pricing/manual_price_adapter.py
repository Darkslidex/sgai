"""
Adaptador de precios Nivel 1 — Entrada Manual.

Confidence: 1.0 — el usuario los vio en el supermercado.
"""

import logging
from datetime import date, datetime

from app.domain.models.market import MarketPrice
from app.domain.ports.market_price_port import MarketPricePort
from app.domain.ports.market_repository import MarketRepositoryPort

logger = logging.getLogger(__name__)


class ManualPriceAdapter(MarketPricePort):
    """Nivel 1 (primario): precios ingresados manualmente vía Telegram.

    Prioridad máxima porque el usuario los verificó físicamente.
    Solo considera precios con source='manual'.
    """

    CONFIDENCE = 1.0
    SOURCE = "manual"

    def __init__(self, market_repo: MarketRepositoryPort) -> None:
        self._repo = market_repo

    async def get_price(self, ingredient_id: int) -> MarketPrice | None:
        """Retorna el precio manual más reciente para el ingrediente."""
        prices = await self._repo.get_prices_by_source(
            ingredient_id, source=self.SOURCE, days=7
        )
        if not prices:
            return None
        # El repo ya retorna ordenado por fecha DESC, tomar el más reciente
        return prices[0]

    async def save_price(
        self,
        ingredient_id: int,
        price_ars: float,
        store: str | None = None,
    ) -> MarketPrice:
        """Persiste un precio manual con confidence 1.0."""
        price = MarketPrice(
            id=0,
            ingredient_id=ingredient_id,
            price_ars=price_ars,
            source=self.SOURCE,
            store=store,
            confidence=self.CONFIDENCE,
            date=date.today(),
            created_at=datetime.utcnow(),
        )
        saved = await self._repo.add_price(price)
        logger.info(
            "Precio manual guardado: ingredient_id=%d, ARS=%.2f, tienda=%s",
            ingredient_id, price_ars, store,
        )
        return saved
