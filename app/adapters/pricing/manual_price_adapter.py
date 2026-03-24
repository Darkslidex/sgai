"""
Adaptador de precios Nivel 1 — Entrada Manual y Facturas.

Confidence: 1.0 — el usuario los vio en el supermercado o subió una factura.
"""

import logging
from datetime import date, datetime

from app.domain.models.market import MarketPrice
from app.domain.ports.market_price_port import MarketPricePort
from app.domain.ports.market_repository import MarketRepositoryPort

logger = logging.getLogger(__name__)

# Fuentes de alta confianza ingresadas por el usuario
_HIGH_CONFIDENCE_SOURCES = ("manual", "factura")


class ManualPriceAdapter(MarketPricePort):
    """Nivel 1 (primario): precios ingresados manualmente o extraídos de facturas.

    Prioridad máxima porque el usuario los verificó físicamente.
    Considera precios con source='manual' o source='factura', válidos por 7 días.
    """

    CONFIDENCE = 1.0
    SOURCE = "manual"

    def __init__(self, market_repo: MarketRepositoryPort) -> None:
        self._repo = market_repo

    async def get_price(self, ingredient_id: int) -> MarketPrice | None:
        """Retorna el precio manual/factura más reciente para el ingrediente."""
        best: MarketPrice | None = None
        for source in _HIGH_CONFIDENCE_SOURCES:
            prices = await self._repo.get_prices_by_source(
                ingredient_id, source=source, days=7
            )
            if prices:
                candidate = prices[0]  # repo retorna DESC por fecha
                if best is None or candidate.date > best.date:
                    best = candidate
        return best

    async def save_price(
        self,
        ingredient_id: int,
        price_ars: float,
        store: str | None = None,
        source: str = "manual",
    ) -> MarketPrice:
        """Persiste un precio manual o de factura con confidence 1.0."""
        price = MarketPrice(
            id=0,
            ingredient_id=ingredient_id,
            price_ars=price_ars,
            source=source,
            store=store,
            confidence=self.CONFIDENCE,
            date=date.today(),
            created_at=datetime.utcnow(),
        )
        saved = await self._repo.add_price(price)
        logger.info(
            "Precio %s guardado: ingredient_id=%d, ARS=%.2f, tienda=%s",
            source, ingredient_id, price_ars, store,
        )
        return saved
