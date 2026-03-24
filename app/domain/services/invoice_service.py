"""
Servicio de procesamiento de facturas/tickets de supermercado.

Flujo:
  1. Recibe bytes de la foto del ticket
  2. Envía a DeepSeek Vision para extracción de items y precios
  3. Matchea los nombres contra el catálogo de ingredientes
  4. Guarda los precios con source='factura', confidence=1.0
  5. Retorna un resumen de lo que se cargó
"""

import base64
import logging
from dataclasses import dataclass

from app.domain.ports.market_repository import MarketRepositoryPort

logger = logging.getLogger(__name__)

_INVOICE_PROMPT = """Analizá esta foto de un ticket o factura de supermercado argentino.

Retorná ÚNICAMENTE un JSON con este formato:
{
  "store": "nombre del supermercado (ej: Coto, Carrefour, Jumbo, Disco, Día, La Anónima)",
  "date": "fecha en formato YYYY-MM-DD o null si no se ve",
  "items": [
    {
      "name": "nombre normalizado del producto en español simple (ej: tomate, pollo, arroz, leche)",
      "price_ars": 1500.0,
      "quantity": 1.0,
      "unit": "kg/g/l/ml/u"
    }
  ]
}

Reglas:
- Normalizá los nombres al ingrediente base (ej: "Tomate perita x1kg" → "tomate")
- Solo incluí alimentos e ingredientes, ignorá bolsas, servicios, impuestos, totales
- El price_ars debe ser el precio unitario (no el subtotal de múltiples unidades)
- Si no podés leer el precio de un item, omitilo
- Si no ves el nombre del supermercado, usá "desconocido"
"""


@dataclass
class InvoiceItem:
    """Item extraído de una factura y matcheado con el catálogo."""
    ingredient_id: int
    ingredient_name: str
    extracted_name: str
    price_ars: float
    store: str


@dataclass
class InvoiceResult:
    """Resultado del procesamiento de una factura."""
    store: str
    date: str | None
    matched_items: list[InvoiceItem]
    unmatched_names: list[str]
    total_saved: int


class InvoiceService:
    """Procesa facturas de supermercado y extrae precios para el catálogo."""

    def __init__(self, llm, market_repo: MarketRepositoryPort, ingredient_repo) -> None:
        self._llm = llm
        self._market_repo = market_repo
        self._ingredient_repo = ingredient_repo

    async def process_invoice(
        self, photo_bytes: bytes, vision_model: str = "deepseek-vl2"
    ) -> InvoiceResult:
        """Procesa una foto de factura y guarda los precios encontrados."""

        # 1. Llamar al LLM de visión
        b64 = base64.b64encode(photo_bytes).decode()
        raw = await self._llm.analyze_invoice(b64, _INVOICE_PROMPT, vision_model)

        store = raw.get("store", "desconocido")
        invoice_date = raw.get("date")
        items = raw.get("items", [])

        # 2. Cargar catálogo de ingredientes para matching
        all_ingredients = await self._ingredient_repo.list_ingredients()
        catalog = self._build_catalog(all_ingredients)

        # 3. Matchear y guardar precios
        matched: list[InvoiceItem] = []
        unmatched: list[str] = []

        for item in items:
            name = item.get("name", "").strip().lower()
            price = item.get("price_ars")
            if not name or not price or price <= 0:
                continue

            ingredient = self._match_ingredient(name, catalog)
            if ingredient is None:
                unmatched.append(name)
                logger.debug("Ingrediente no encontrado en catálogo: '%s'", name)
                continue

            from datetime import date, datetime
            from app.domain.models.market import MarketPrice

            market_price = MarketPrice(
                id=0,
                ingredient_id=ingredient["id"],
                price_ars=float(price),
                source="factura",
                store=store,
                confidence=1.0,
                date=date.today(),
                created_at=datetime.utcnow(),
            )
            await self._market_repo.add_price(market_price)

            matched.append(InvoiceItem(
                ingredient_id=ingredient["id"],
                ingredient_name=ingredient["name"],
                extracted_name=name,
                price_ars=float(price),
                store=store,
            ))
            logger.info(
                "Factura: guardado %s → %s ARS=%.2f tienda=%s",
                name, ingredient["name"], float(price), store,
            )

        return InvoiceResult(
            store=store,
            date=invoice_date,
            matched_items=matched,
            unmatched_names=unmatched,
            total_saved=len(matched),
        )

    def _build_catalog(self, ingredients: list) -> list[dict]:
        """Construye una lista de {id, name, aliases} para matching."""
        catalog = []
        for ing in ingredients:
            aliases = ing.aliases if hasattr(ing, "aliases") and ing.aliases else []
            catalog.append({
                "id": ing.id,
                "name": ing.name.lower(),
                "aliases": [a.lower() for a in aliases],
            })
        return catalog

    def _match_ingredient(self, name: str, catalog: list[dict]) -> dict | None:
        """Busca el ingrediente más cercano al nombre extraído.

        Estrategia:
        1. Match exacto por nombre
        2. Match exacto por alias
        3. El nombre extraído contiene el nombre del ingrediente (o viceversa)
        """
        name_lower = name.lower()

        # Exact match
        for ing in catalog:
            if ing["name"] == name_lower:
                return ing
            if name_lower in ing["aliases"]:
                return ing

        # Contains match
        for ing in catalog:
            if ing["name"] in name_lower or name_lower in ing["name"]:
                return ing
            for alias in ing["aliases"]:
                if alias in name_lower or name_lower in alias:
                    return ing

        return None
