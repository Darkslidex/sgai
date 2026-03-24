"""Servicio de procesamiento de tickets de compra enviados por Ana.

A diferencia de InvoiceService (que llama a DeepSeek Vision para extraer los datos),
ReceiptService recibe los datos YA PARSEADOS por Ana y se encarga de:
1. Hacer fuzzy matching de cada nombre de producto contra el catálogo de ingredientes
   usando pg_trgm (con fallback a ILIKE + Python si pg_trgm no está disponible).
2. Registrar los precios en market_prices con source='receipt', confidence=1.0.
3. Retornar un resumen de los ítems registrados y los que no tuvieron match.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime

from app.adapters.persistence.ingredient_repo import IngredientRepository
from app.adapters.persistence.market_repo import MarketRepository
from app.domain.models.market import MarketPrice

logger = logging.getLogger(__name__)


@dataclass
class ReceiptItemResult:
    product_name: str
    matched_ingredient_id: int | None
    matched_ingredient_name: str | None
    price_ars: float
    registered: bool


@dataclass
class ReceiptProcessingResult:
    store_name: str
    purchase_date: date
    registered: int
    skipped: int
    skipped_items: list[str]
    detail: list[ReceiptItemResult]


class ReceiptService:
    """Procesa ítems de tickets de compra ya parseados por Ana."""

    def __init__(
        self,
        ingredient_repo: IngredientRepository,
        market_repo: MarketRepository,
    ) -> None:
        self._ing_repo = ingredient_repo
        self._market_repo = market_repo

    async def process_items(
        self,
        store_name: str,
        purchase_date: date,
        items: list[dict],
        fuzzy_threshold: float = 0.3,
    ) -> ReceiptProcessingResult:
        """Procesa una lista de ítems {product_name, price_ars, quantity}.

        Estrategia de matching (en orden de preferencia):
        1. Fuzzy match con pg_trgm (similarity > threshold)
        2. Fallback: ILIKE + contains match en Python contra aliases
        """
        detail: list[ReceiptItemResult] = []

        for item in items:
            product_name: str = item.get("product_name", "").strip()
            price_ars: float = float(item.get("price_ars", 0))

            if not product_name or price_ars <= 0:
                continue

            ingredient = await self._find_best_match(product_name, fuzzy_threshold)

            if ingredient is None:
                detail.append(ReceiptItemResult(
                    product_name=product_name,
                    matched_ingredient_id=None,
                    matched_ingredient_name=None,
                    price_ars=price_ars,
                    registered=False,
                ))
                logger.debug("Sin match para '%s'", product_name)
                continue

            market_price = MarketPrice(
                id=0,
                ingredient_id=ingredient.id,
                price_ars=price_ars,
                source="receipt",
                store=store_name,
                confidence=1.0,
                date=purchase_date,
                created_at=datetime.utcnow(),
            )
            await self._market_repo.add_price(market_price)

            detail.append(ReceiptItemResult(
                product_name=product_name,
                matched_ingredient_id=ingredient.id,
                matched_ingredient_name=ingredient.name,
                price_ars=price_ars,
                registered=True,
            ))
            logger.info(
                "Receipt: '%s' → '%s' (id=%d) ARS=%.2f tienda=%s",
                product_name, ingredient.name, ingredient.id, price_ars, store_name,
            )

        registered = sum(1 for r in detail if r.registered)
        skipped_items = [r.product_name for r in detail if not r.registered]

        return ReceiptProcessingResult(
            store_name=store_name,
            purchase_date=purchase_date,
            registered=registered,
            skipped=len(skipped_items),
            skipped_items=skipped_items,
            detail=detail,
        )

    async def _find_best_match(self, product_name: str, threshold: float):
        """Busca el ingrediente más cercano al nombre del producto.

        1. Fuzzy match pg_trgm
        2. Si no hay resultado: ILIKE
        3. Si hay resultados ILIKE pero ninguno es bueno: contains match en Python
        """
        # 1. Fuzzy (pg_trgm o ILIKE fallback)
        matches = await self._ing_repo.search_ingredients_fuzzy(product_name, threshold)
        if matches:
            return matches[0]

        # 2. Contains match en Python contra nombre + aliases
        all_ingredients = await self._ing_repo.list_ingredients()
        name_lower = product_name.lower()
        for ing in all_ingredients:
            if ing.name.lower() in name_lower or name_lower in ing.name.lower():
                return ing
            aliases = ing.aliases or []
            for alias in aliases:
                alias_lower = alias.lower()
                if alias_lower in name_lower or name_lower in alias_lower:
                    return ing

        return None
