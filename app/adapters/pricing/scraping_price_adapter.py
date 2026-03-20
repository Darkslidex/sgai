"""
Adaptador de precios Nivel 3 — Scraping liviano.

Confidence: 0.6
Circuit breaker: 3 fallos consecutivos → desactivado por 1 hora.
"""

import logging
from datetime import date, datetime, timedelta

import httpx

from app.domain.models.market import MarketPrice
from app.domain.ports.market_price_port import MarketPricePort
from app.domain.ports.market_repository import MarketRepositoryPort

logger = logging.getLogger(__name__)


class ScrapingPriceAdapter(MarketPricePort):
    """Nivel 3 (terciario): scraping liviano de supermercados online.

    Circuit breaker: si falla MAX_FAILURES veces seguidas, se desactiva por COOLDOWN_SECONDS.
    La instancia es compartida (singleton) para mantener el estado del circuit breaker.
    """

    CONFIDENCE = 0.6
    SOURCE = "scraping"
    MAX_FAILURES = 3
    COOLDOWN_SECONDS = 3600  # 1 hora
    TIMEOUT_SECONDS = 15

    # URL base del supermercado a scrapear (Coto como ejemplo)
    _SCRAPE_BASE_URL = "https://www.cotodigital3.com.ar/sitios/cdigi/browse"

    def __init__(self, market_repo: MarketRepositoryPort) -> None:
        self._repo = market_repo
        self.failure_count: int = 0
        self.circuit_open_until: datetime | None = None
        self._ingredient_names: dict[int, str] = {}

    def register_ingredient(self, ingredient_id: int, name: str) -> None:
        """Registra el nombre de un ingrediente para búsqueda."""
        self._ingredient_names[ingredient_id] = name.lower()

    def _is_circuit_open(self) -> bool:
        """Retorna True si el circuit breaker está activado."""
        if self.circuit_open_until is None:
            return False
        if datetime.now() >= self.circuit_open_until:
            # Cooldown terminó: resetear
            self.circuit_open_until = None
            self.failure_count = 0
            logger.info("Circuit breaker de scraping reseteado después del cooldown.")
            return False
        return True

    def _record_failure(self) -> None:
        """Registra un fallo y activa el circuit breaker si corresponde."""
        self.failure_count += 1
        if self.failure_count >= self.MAX_FAILURES:
            self.circuit_open_until = datetime.now() + timedelta(seconds=self.COOLDOWN_SECONDS)
            logger.warning(
                "Circuit breaker ABIERTO: %d fallos consecutivos. "
                "Scraping desactivado hasta %s.",
                self.failure_count,
                self.circuit_open_until.strftime("%H:%M:%S"),
            )

    def _record_success(self) -> None:
        """Resetea el contador de fallos en caso de éxito."""
        self.failure_count = 0

    async def get_price(self, ingredient_id: int) -> MarketPrice | None:
        """Scrapea el precio del ingrediente. Retorna None si el circuit está abierto."""
        if self._is_circuit_open():
            logger.debug(
                "Circuit breaker abierto — saltando scraping para ingredient_id=%d", ingredient_id
            )
            return None

        name = self._ingredient_names.get(ingredient_id, "")
        if not name:
            return None

        try:
            price_ars = await self._scrape_price(name)
            if price_ars is None:
                self._record_failure()
                return None

            self._record_success()
            return await self.save_price(ingredient_id, price_ars, store="Coto")

        except Exception as exc:
            logger.warning("Scraping falló para ingredient_id=%d: %s", ingredient_id, exc)
            self._record_failure()
            return None

    async def _scrape_price(self, ingredient_name: str) -> float | None:
        """Intenta obtener el precio scrapeando el supermercado.

        Implementación liviana: busca en la web del supermercado y extrae precio.
        Retorna None si no puede encontrar el producto.
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                resp = await client.get(
                    self._SCRAPE_BASE_URL,
                    params={"_dyncharset": "utf-8", "Ntt": ingredient_name},
                    headers={"User-Agent": "Mozilla/5.0 (compatible; SGAI/1.0)"},
                )
                resp.raise_for_status()
                # Extracción básica de precio del HTML
                return self._extract_price_from_html(resp.text)
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.debug("Scraping HTTP error para '%s': %s", ingredient_name, exc)
            raise

    def _extract_price_from_html(self, html: str) -> float | None:
        """Extrae el primer precio encontrado en el HTML.

        Busca patrones como '$1.500' o '1500.00' en el contenido.
        Retorna None si no encuentra ningún precio.
        """
        import re
        # Patrón para precios ARS: $1.500 o 1500,50 o similares
        patterns = [
            r'\$\s*([\d\.]+)',           # $1.500
            r'precio[^>]*>([\d\.]+)',     # precio>1500
            r'"price":\s*"?([\d\.]+)',    # JSON price
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for m in matches:
                try:
                    # Normalizar: remover puntos como separadores de miles
                    clean = m.replace(".", "").replace(",", ".")
                    price = float(clean)
                    if 10 < price < 100_000:  # Rango razonable para ARS
                        return price
                except ValueError:
                    continue
        return None

    async def save_price(
        self,
        ingredient_id: int,
        price_ars: float,
        store: str | None = None,
    ) -> MarketPrice:
        """Persiste el precio scrapeado en la DB."""
        price = MarketPrice(
            id=0,
            ingredient_id=ingredient_id,
            price_ars=price_ars,
            source=self.SOURCE,
            store=store or "scraping",
            confidence=self.CONFIDENCE,
            date=date.today(),
            created_at=datetime.utcnow(),
        )
        return await self._repo.add_price(price)
