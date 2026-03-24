"""
Servicio unificado de precios — estrategia híbrida 2 niveles.

Prioridad: Manual/Factura (1.0) > SEPA (0.8) > Último conocido (fallback)
"""

import logging

from app.domain.models.market import MarketPrice
from app.domain.ports.market_price_port import MarketPricePort
from app.domain.ports.market_repository import MarketRepositoryPort

logger = logging.getLogger(__name__)

_MAX_MANUAL_DAYS = 7        # Precio manual/factura válido por 7 días
_ANOMALY_HIGH_FACTOR = 1.5  # Salto > 50% en un día → anomalía
_ANOMALY_LOW_FACTOR = 0.3   # Caída > 70% → posible error de tipeo
_ANOMALY_MIN_HISTORY = 3    # Mínimo de registros para detectar anomalía


class PriceService:
    """Orquesta la estrategia híbrida de precios con fallback automático.

    Orden de resolución:
    1. ManualPriceAdapter (visto en góndola o extraído de factura — máxima confianza)
    2. SEPAPriceAdapter (API gobierno argentino — confianza alta)
    3. Último precio conocido en DB (fallback con warning de antigüedad)
    """

    def __init__(
        self,
        manual_adapter: MarketPricePort,
        sepa_adapter: MarketPricePort,
        market_repo: MarketRepositoryPort,
    ) -> None:
        self._manual = manual_adapter
        self._sepa = sepa_adapter
        self._repo = market_repo

    async def get_best_price(self, ingredient_id: int) -> MarketPrice | None:
        """Retorna el mejor precio disponible según la estrategia híbrida."""

        # 1. Precio manual o de factura (máxima confianza, válido 7 días)
        price = await self._manual.get_price(ingredient_id)
        if price and self._is_recent(price, max_days=_MAX_MANUAL_DAYS):
            logger.debug(
                "Precio %s usado para ingredient_id=%d: ARS=%.2f",
                price.source, ingredient_id, price.price_ars,
            )
            return price

        # 2. API SEPA (confianza alta, falla gracefully)
        price = await self._sepa.get_price(ingredient_id)
        if price:
            logger.debug(
                "Precio SEPA usado para ingredient_id=%d: ARS=%.2f",
                ingredient_id, price.price_ars,
            )
            return price

        # 3. Último precio conocido (fallback)
        fallback = await self._get_last_known_price(ingredient_id)
        if fallback:
            logger.warning(
                "Usando último precio conocido para ingredient_id=%d (fecha: %s). "
                "Ninguna fuente disponible.",
                ingredient_id, fallback.date,
            )
        return fallback

    async def detect_price_anomaly(self, ingredient_id: int, new_price: float) -> bool:
        """Detecta si un precio es anómalo comparado con el historial de 30 días."""
        history = await self._repo.get_price_history(ingredient_id, days=30)
        if len(history) < _ANOMALY_MIN_HISTORY:
            return False

        avg = sum(p.price_ars for p in history) / len(history)

        if new_price > avg * _ANOMALY_HIGH_FACTOR:
            logger.warning(
                "Anomalía de precio detectada (alto): ingredient_id=%d, "
                "nuevo=%.2f, promedio_30d=%.2f (+%.0f%%)",
                ingredient_id, new_price, avg,
                (new_price / avg - 1) * 100,
            )
            return True

        if new_price < avg * _ANOMALY_LOW_FACTOR:
            logger.warning(
                "Anomalía de precio detectada (bajo): ingredient_id=%d, "
                "nuevo=%.2f, promedio_30d=%.2f (%.0f%%)",
                ingredient_id, new_price, avg,
                (new_price / avg - 1) * 100,
            )
            return True

        return False

    async def get_prices_for_plan(self, ingredient_ids: list[int]) -> dict[int, MarketPrice]:
        """Retorna el mejor precio para cada ingrediente de un plan."""
        result: dict[int, MarketPrice] = {}
        for ingredient_id in ingredient_ids:
            price = await self.get_best_price(ingredient_id)
            if price:
                result[ingredient_id] = price
        return result

    async def get_best_prices_by_store(
        self, ingredient_ids: list[int], days: int = 30
    ) -> dict[str, dict[int, float]]:
        """Retorna el mejor precio por supermercado para una lista de ingredientes.

        Returns:
            Dict store_name -> {ingredient_id -> best_price_ars}
        """
        store_prices: dict[str, dict[int, float]] = {}
        for ingredient_id in ingredient_ids:
            history = await self._repo.get_price_history(ingredient_id, days=days)
            for record in history:
                if not record.store:
                    continue
                store = record.store
                if store not in store_prices:
                    store_prices[store] = {}
                existing = store_prices[store].get(ingredient_id)
                if existing is None or record.price_ars < existing:
                    store_prices[store][ingredient_id] = record.price_ars
        return store_prices

    def _is_recent(self, price: MarketPrice, max_days: int) -> bool:
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=max_days)
        return price.date >= cutoff

    async def _get_last_known_price(self, ingredient_id: int) -> MarketPrice | None:
        return await self._repo.get_current_price(ingredient_id)
