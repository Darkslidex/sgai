"""
Adaptador de precios Nivel 2 — API SEPA.

Secretaría de Comercio Argentina — Precios Cuidados.
Confidence: 0.8
Degradación graceful: timeout / errores HTTP → retorna None sin levantar excepción.
Timeout: 10s. Retry: 2 intentos.
"""

import logging
from datetime import date, datetime

import httpx

from app.domain.models.market import MarketPrice
from app.domain.ports.market_price_port import MarketPricePort
from app.domain.ports.market_repository import MarketRepositoryPort

logger = logging.getLogger(__name__)

# Mapeo básico de nombre canónico de ingrediente a término de búsqueda SEPA
_SEPA_SEARCH_TERMS: dict[str, str] = {
    "pollo": "pollo",
    "carne picada": "carne picada",
    "carne": "carne",
    "arroz": "arroz",
    "fideos": "fideos",
    "papa": "papa",
    "tomate": "tomate",
    "cebolla": "cebolla",
    "leche": "leche",
    "huevo": "huevo",
    "aceite": "aceite girasol",
    "harina": "harina",
    "lentejas": "lentejas",
    "garbanzos": "garbanzos",
    "atún": "atun",
    "sardina": "sardina",
}


class SEPAPriceAdapter(MarketPricePort):
    """Nivel 2 (secundario): API SEPA con degradación graceful.

    Si SEPA no responde o retorna error, retorna None en lugar de propagar la excepción.
    Esto garantiza que el sistema siga funcionando con precios manuales o scraping.
    """

    CONFIDENCE = 0.8
    SOURCE = "sepa"
    SEPA_BASE_URL = "https://www.argentina.gob.ar/api/sepa/productos"
    TIMEOUT_SECONDS = 10
    MAX_RETRIES = 2

    def __init__(
        self,
        market_repo: MarketRepositoryPort,
        ingredient_names: dict[int, str] | None = None,
    ) -> None:
        self._repo = market_repo
        # Mapeo ingrediente_id → nombre canónico para búsqueda en SEPA
        self._ingredient_names: dict[int, str] = ingredient_names or {}

    def register_ingredient(self, ingredient_id: int, name: str) -> None:
        """Registra el nombre de un ingrediente para búsqueda SEPA."""
        self._ingredient_names[ingredient_id] = name.lower()

    async def get_price(self, ingredient_id: int) -> MarketPrice | None:
        """Consulta SEPA por el precio del ingrediente. Degrada gracefully ante errores."""
        name = self._ingredient_names.get(ingredient_id, "")
        search_term = _SEPA_SEARCH_TERMS.get(name, name)
        if not search_term:
            return None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                    resp = await client.get(
                        self.SEPA_BASE_URL,
                        params={"q": search_term, "limit": 5},
                    )
                    resp.raise_for_status()
                    data = resp.json()

                price_ars = self._parse_sepa_response(data, search_term)
                if price_ars is None:
                    return None

                return await self.save_price(ingredient_id, price_ars, store="SEPA")

            except httpx.TimeoutException:
                logger.warning(
                    "SEPA timeout (intento %d/%d) para ingredient_id=%d",
                    attempt + 1, self.MAX_RETRIES, ingredient_id,
                )
            except httpx.HTTPError as exc:
                logger.warning(
                    "SEPA HTTP error (intento %d/%d) ingredient_id=%d: %s",
                    attempt + 1, self.MAX_RETRIES, ingredient_id, exc,
                )
            except Exception as exc:
                logger.warning(
                    "SEPA error inesperado ingredient_id=%d: %s", ingredient_id, exc
                )
                return None  # No reintentar errores inesperados

        logger.warning(
            "SEPA no disponible después de %d intentos para ingredient_id=%d, degradando.",
            self.MAX_RETRIES, ingredient_id,
        )
        return None

    async def save_price(
        self,
        ingredient_id: int,
        price_ars: float,
        store: str | None = None,
    ) -> MarketPrice:
        """Persiste el precio SEPA en la DB."""
        price = MarketPrice(
            id=0,
            ingredient_id=ingredient_id,
            price_ars=price_ars,
            source=self.SOURCE,
            store=store or "SEPA",
            confidence=self.CONFIDENCE,
            date=date.today(),
            created_at=datetime.utcnow(),
        )
        return await self._repo.add_price(price)

    def _parse_sepa_response(self, data: dict | list, search_term: str) -> float | None:
        """Extrae el precio promedio de la respuesta SEPA.

        El formato exacto puede variar; esta implementación maneja el caso general.
        """
        try:
            items = data if isinstance(data, list) else data.get("results", data.get("items", []))
            if not items:
                return None

            prices = []
            for item in items[:5]:  # Máximo 5 resultados
                # Diferentes campos posibles según versión de la API
                price = (
                    item.get("precio_max")
                    or item.get("precio_promedio")
                    or item.get("precio")
                    or item.get("price")
                )
                if price is not None:
                    prices.append(float(price))

            return sum(prices) / len(prices) if prices else None
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("Error parseando respuesta SEPA: %s", exc)
            return None
