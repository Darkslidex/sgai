"""
Seed de precios referenciales en ARS (marzo 2026, CABA, Argentina).
Fuente: estimaciones para supermercados de Recoleta.
Marcados como confidence=0.5, source="seed".
Idempotente: solo inserta si el ingrediente no tiene precio seed previo.
"""

import asyncio
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.market_price_orm import MarketPriceORM

logger = logging.getLogger(__name__)

# precio_ars es por unidad de medida del ingrediente (kg, litro, unidad)
PRICES: list[dict] = [
    # PROTEÍNAS ANIMALES
    {"ingredient_name": "pechuga de pollo",  "price_ars": 5500.0},
    {"ingredient_name": "muslo de pollo",    "price_ars": 4800.0},
    {"ingredient_name": "carne picada",      "price_ars": 6800.0},
    {"ingredient_name": "nalga",             "price_ars": 7500.0},
    {"ingredient_name": "cerdo bondiola",    "price_ars": 5200.0},
    {"ingredient_name": "merluza",           "price_ars": 4500.0},
    {"ingredient_name": "atun en lata",      "price_ars": 1800.0},   # por lata 170g
    {"ingredient_name": "huevo",             "price_ars": 350.0},    # por unidad
    {"ingredient_name": "salmon",            "price_ars": 8500.0},
    {"ingredient_name": "sardinas en lata",  "price_ars": 1500.0},   # por lata
    # PROTEÍNAS VEGETALES
    {"ingredient_name": "lentejas",          "price_ars": 2500.0},
    {"ingredient_name": "garbanzos",         "price_ars": 2800.0},
    {"ingredient_name": "porotos negros",    "price_ars": 2400.0},
    {"ingredient_name": "porotos blancos",   "price_ars": 2200.0},
    {"ingredient_name": "soja texturizada",  "price_ars": 1800.0},
    {"ingredient_name": "ricota",            "price_ars": 2800.0},
    {"ingredient_name": "queso cottage",     "price_ars": 3200.0},
    {"ingredient_name": "pechuga de pavo",   "price_ars": 6200.0},
    # VERDURAS
    {"ingredient_name": "tomate",            "price_ars": 2200.0},
    {"ingredient_name": "cebolla",           "price_ars": 1400.0},
    {"ingredient_name": "morron rojo",       "price_ars": 3500.0},
    {"ingredient_name": "zapallito",         "price_ars": 1800.0},
    {"ingredient_name": "papa",              "price_ars": 1200.0},
    {"ingredient_name": "batata",            "price_ars": 1500.0},
    {"ingredient_name": "zanahoria",         "price_ars": 1100.0},
    {"ingredient_name": "brocoli",           "price_ars": 2800.0},
    {"ingredient_name": "espinaca",          "price_ars": 2500.0},
    {"ingredient_name": "apio",              "price_ars": 1600.0},
    {"ingredient_name": "zapallo",           "price_ars": 1000.0},
    {"ingredient_name": "choclo",            "price_ars": 800.0},    # por unidad
    {"ingredient_name": "acelga",            "price_ars": 1200.0},
    {"ingredient_name": "repollo",           "price_ars": 900.0},
    {"ingredient_name": "berenjena",         "price_ars": 2000.0},
    {"ingredient_name": "lechuga",           "price_ars": 1800.0},
    {"ingredient_name": "pepino",            "price_ars": 1600.0},
    {"ingredient_name": "cebolla de verdeo", "price_ars": 1800.0},
    # CARBOHIDRATOS
    {"ingredient_name": "arroz",             "price_ars": 1800.0},
    {"ingredient_name": "fideos",            "price_ars": 2200.0},
    {"ingredient_name": "pan integral",      "price_ars": 2800.0},   # por unidad 400g
    {"ingredient_name": "avena",             "price_ars": 1500.0},
    {"ingredient_name": "quinoa",            "price_ars": 4500.0},
    {"ingredient_name": "arroz integral",    "price_ars": 2200.0},
    {"ingredient_name": "polenta",           "price_ars": 1200.0},
    {"ingredient_name": "pan de molde",      "price_ars": 2500.0},   # por unidad 500g
    {"ingredient_name": "harina de trigo",   "price_ars": 900.0},
    {"ingredient_name": "fideos integrales", "price_ars": 2800.0},
    # LÁCTEOS
    {"ingredient_name": "queso cremoso",     "price_ars": 7500.0},
    {"ingredient_name": "leche entera",      "price_ars": 1200.0},   # por litro
    {"ingredient_name": "yogur natural",     "price_ars": 1800.0},
    {"ingredient_name": "manteca",           "price_ars": 4500.0},
    {"ingredient_name": "crema de leche",    "price_ars": 2800.0},   # por litro
    {"ingredient_name": "queso rallado",     "price_ars": 9500.0},
    {"ingredient_name": "mozzarella",        "price_ars": 8000.0},
    # CONDIMENTOS
    {"ingredient_name": "aceite de oliva",   "price_ars": 8500.0},   # por litro
    {"ingredient_name": "sal",               "price_ars": 600.0},
    {"ingredient_name": "ajo",               "price_ars": 3500.0},   # por kg
    {"ingredient_name": "oregano",           "price_ars": 3000.0},   # por kg (aprox 800 pack)
    {"ingredient_name": "pimenton",          "price_ars": 4000.0},   # por kg
    {"ingredient_name": "comino",            "price_ars": 4500.0},   # por kg
    {"ingredient_name": "pimienta negra",    "price_ars": 5000.0},   # por kg
    {"ingredient_name": "aceite de girasol", "price_ars": 2800.0},   # por litro
    {"ingredient_name": "vinagre",           "price_ars": 1200.0},   # por litro
    {"ingredient_name": "salsa de tomate",   "price_ars": 1500.0},   # por unidad 500g
    {"ingredient_name": "caldo de pollo",    "price_ars": 600.0},    # por caja pastillas
    {"ingredient_name": "laurel",            "price_ars": 2000.0},   # por kg
]


async def seed_prices(session: AsyncSession, name_to_id: dict[str, int]) -> None:
    """Inserta precios referenciales para ingredientes sin precio seed previo."""
    # Cargar precios seed ya existentes
    existing = await session.execute(
        select(MarketPriceORM).where(MarketPriceORM.source == "seed")
    )
    existing_ingredient_ids = {row.ingredient_id for row in existing.scalars()}

    today = date.today()
    created = 0
    skipped = 0

    for data in PRICES:
        ing_name = data["ingredient_name"]
        ing_id = name_to_id.get(ing_name)
        if ing_id is None:
            logger.warning("Ingrediente no encontrado para precio: %s", ing_name)
            continue
        if ing_id in existing_ingredient_ids:
            skipped += 1
            continue

        orm = MarketPriceORM(
            ingredient_id=ing_id,
            price_ars=data["price_ars"],
            source="seed",
            store=None,
            confidence=0.5,
            date=today,
        )
        session.add(orm)
        created += 1

    await session.flush()
    logger.info("Precios: %d nuevos, %d ya existían", created, skipped)


if __name__ == "__main__":
    async def _main():
        from app.config import get_settings
        from app.database import init_db, get_session
        from sqlalchemy import select
        from app.adapters.persistence.ingredient_orm import IngredientORM
        settings = get_settings()
        init_db(settings.database_url)
        async with get_session() as session:
            result = await session.execute(select(IngredientORM))
            name_to_id = {row.name: row.id for row in result.scalars()}
            await seed_prices(session, name_to_id)
            print("✅ Precios cargados")

    asyncio.run(_main())
