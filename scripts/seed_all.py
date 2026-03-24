"""
Script maestro de seed para SGAI.
Ejecuta: ingredientes → precios → recetas en orden, idempotente.

Uso:
    python -m scripts.seed_all
"""

import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def _run_seed() -> None:
    # Setear vars de entorno mínimas si no están (para entorno de desarrollo)
    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL no está configurada")
        sys.exit(1)

    from app.adapters.persistence.ingredient_orm import IngredientORM  # noqa: F401 - ensure ORM registered
    from app.config import get_settings
    from app.database import get_session, init_db
    from scripts.seed_ingredients import seed_ingredients
    from scripts.seed_prices import seed_prices
    from scripts.seed_recipes import seed_recipes

    settings = get_settings()
    init_db(settings.database_url)

    async with get_session() as session:
        logger.info("── Paso 1: Ingredientes ─────────────────")
        name_to_id = await seed_ingredients(session)
        logger.info("   %d ingredientes disponibles", len(name_to_id))

        logger.info("── Paso 2: Precios referenciales ────────")
        await seed_prices(session, name_to_id)

        logger.info("── Paso 3: Recetas batch cooking ────────")
        await seed_recipes(session, name_to_id)

    logger.info("✅ Seed completado exitosamente")


def main() -> None:
    asyncio.run(_run_seed())


if __name__ == "__main__":
    main()
