"""
Seed de 65 ingredientes para SGAI.
Organizados por categoría. Idempotente (no duplica si ya existe por nombre).

Uso: python -m scripts.seed_all
"""

import asyncio
import logging
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.persistence.ingredient_orm import IngredientORM

logger = logging.getLogger(__name__)

# ── Datos ─────────────────────────────────────────────────────────────────────
# campos: name, aliases, category, storage_type, unit, protein, calories, shelf_days

INGREDIENTS: list[dict] = [
    # ── PROTEÍNAS ANIMALES (10) ──────────────────────────────────────────────
    {
        "name": "pechuga de pollo", "aliases": ["pechuga", "pollo pechuga", "pollo"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 31.0, "calories_per_100g": 165.0, "avg_shelf_life_days": 3,
    },
    {
        "name": "muslo de pollo", "aliases": ["muslo", "pollo muslo", "pata muslo"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 27.0, "calories_per_100g": 215.0, "avg_shelf_life_days": 3,
    },
    {
        "name": "carne picada", "aliases": ["picada", "carne molida", "picada comun"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 26.0, "calories_per_100g": 250.0, "avg_shelf_life_days": 2,
    },
    {
        "name": "nalga", "aliases": ["nalga de res", "bife de nalga"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 28.0, "calories_per_100g": 180.0, "avg_shelf_life_days": 3,
    },
    {
        "name": "cerdo bondiola", "aliases": ["bondiola", "bondiola de cerdo"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 27.0, "calories_per_100g": 300.0, "avg_shelf_life_days": 3,
    },
    {
        "name": "merluza", "aliases": ["filet de merluza", "merluza filet"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 17.0, "calories_per_100g": 80.0, "avg_shelf_life_days": 2,
    },
    {
        "name": "atun en lata", "aliases": ["atun", "lata de atun", "atún en lata", "atún"],
        "category": "proteina", "storage_type": "seco", "unit": "unidad",
        "protein_per_100g": 25.0, "calories_per_100g": 116.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "huevo", "aliases": ["huevos", "huevo de gallina"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "unidad",
        "protein_per_100g": 13.0, "calories_per_100g": 155.0, "avg_shelf_life_days": 21,
    },
    {
        "name": "salmon", "aliases": ["filet de salmon", "salmon rosado"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 20.0, "calories_per_100g": 208.0, "avg_shelf_life_days": 2,
    },
    {
        "name": "sardinas en lata", "aliases": ["sardinas", "lata de sardinas"],
        "category": "proteina", "storage_type": "seco", "unit": "unidad",
        "protein_per_100g": 25.0, "calories_per_100g": 208.0, "avg_shelf_life_days": 365,
    },
    # ── PROTEÍNAS VEGETALES (8) ──────────────────────────────────────────────
    {
        "name": "lentejas", "aliases": ["lenteja", "lentejas secas"],
        "category": "proteina", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 9.0, "calories_per_100g": 116.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "garbanzos", "aliases": ["garbanzo", "garbanzos secos"],
        "category": "proteina", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 9.0, "calories_per_100g": 164.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "porotos negros", "aliases": ["poroto negro", "frijoles negros"],
        "category": "proteina", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 9.0, "calories_per_100g": 132.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "porotos blancos", "aliases": ["poroto blanco", "alubias"],
        "category": "proteina", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 7.0, "calories_per_100g": 127.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "soja texturizada", "aliases": ["soja", "proteina de soja", "pvt"],
        "category": "proteina", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 50.0, "calories_per_100g": 330.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "ricota", "aliases": ["ricotta"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 11.0, "calories_per_100g": 174.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "queso cottage", "aliases": ["cottage"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 11.0, "calories_per_100g": 98.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "pechuga de pavo", "aliases": ["pavo pechuga", "fiambre de pavo"],
        "category": "proteina", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 29.0, "calories_per_100g": 135.0, "avg_shelf_life_days": 3,
    },
    # ── VERDURAS (18) ────────────────────────────────────────────────────────
    {
        "name": "tomate", "aliases": ["tomates", "tomate perita", "tomate redondo"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 18.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "cebolla", "aliases": ["cebollas", "cebolla blanca", "cebolla morada"],
        "category": "verdura", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 40.0, "avg_shelf_life_days": 30,
    },
    {
        "name": "morron rojo", "aliases": ["pimiento rojo", "morron", "morrón rojo", "morrón"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 31.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "zapallito", "aliases": ["zapallitos", "calabacin"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 17.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "papa", "aliases": ["papas", "patata", "papa blanca"],
        "category": "verdura", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 2.0, "calories_per_100g": 77.0, "avg_shelf_life_days": 30,
    },
    {
        "name": "batata", "aliases": ["batatas", "boniato", "camote"],
        "category": "verdura", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 2.0, "calories_per_100g": 86.0, "avg_shelf_life_days": 30,
    },
    {
        "name": "zanahoria", "aliases": ["zanahorias"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 41.0, "avg_shelf_life_days": 14,
    },
    {
        "name": "brocoli", "aliases": ["brócoli", "brocoli fresco"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 3.0, "calories_per_100g": 34.0, "avg_shelf_life_days": 5,
    },
    {
        "name": "espinaca", "aliases": ["espinacas", "espinaca fresca"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 3.0, "calories_per_100g": 23.0, "avg_shelf_life_days": 4,
    },
    {
        "name": "apio", "aliases": ["apio fresco"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 16.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "zapallo", "aliases": ["zapallo criollo", "calabaza"],
        "category": "verdura", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 26.0, "avg_shelf_life_days": 60,
    },
    {
        "name": "choclo", "aliases": ["maiz", "choclo fresco", "elote"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "unidad",
        "protein_per_100g": 3.0, "calories_per_100g": 86.0, "avg_shelf_life_days": 3,
    },
    {
        "name": "acelga", "aliases": ["acelgas"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 2.0, "calories_per_100g": 20.0, "avg_shelf_life_days": 4,
    },
    {
        "name": "repollo", "aliases": ["repollo blanco", "col"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 25.0, "avg_shelf_life_days": 14,
    },
    {
        "name": "berenjena", "aliases": ["berenjenas"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 25.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "lechuga", "aliases": ["lechuga criolla", "lechuga romana"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 15.0, "avg_shelf_life_days": 5,
    },
    {
        "name": "pepino", "aliases": ["pepinos"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 16.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "cebolla de verdeo", "aliases": ["verdeo", "cebollita de verdeo"],
        "category": "verdura", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 2.0, "calories_per_100g": 32.0, "avg_shelf_life_days": 7,
    },
    # ── CARBOHIDRATOS (10) ───────────────────────────────────────────────────
    {
        "name": "arroz", "aliases": ["arroz blanco", "arroz largo fino"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 7.0, "calories_per_100g": 365.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "fideos", "aliases": ["pasta", "tallarines", "spaghetti", "espagueti"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 12.0, "calories_per_100g": 358.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "pan integral", "aliases": ["pan negro", "pan de salvado"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "unidad",
        "protein_per_100g": 9.0, "calories_per_100g": 247.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "avena", "aliases": ["avena arrollada", "copos de avena"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 13.0, "calories_per_100g": 389.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "quinoa", "aliases": ["quinua"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 14.0, "calories_per_100g": 368.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "arroz integral", "aliases": ["arroz negro", "arroz yamaní"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 8.0, "calories_per_100g": 362.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "polenta", "aliases": ["harina de maiz", "mamag"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 8.0, "calories_per_100g": 350.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "pan de molde", "aliases": ["pan lactal", "pan blanco"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "unidad",
        "protein_per_100g": 9.0, "calories_per_100g": 265.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "harina de trigo", "aliases": ["harina", "harina 000", "harina 0000"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 10.0, "calories_per_100g": 364.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "fideos integrales", "aliases": ["pasta integral", "tallarines integrales"],
        "category": "carbohidrato", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 13.0, "calories_per_100g": 348.0, "avg_shelf_life_days": 365,
    },
    # ── LÁCTEOS (7) ──────────────────────────────────────────────────────────
    {
        "name": "queso cremoso", "aliases": ["queso crema", "cremoso"],
        "category": "lacteo", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 14.0, "calories_per_100g": 300.0, "avg_shelf_life_days": 14,
    },
    {
        "name": "leche entera", "aliases": ["leche", "leche fluida"],
        "category": "lacteo", "storage_type": "refrigerado", "unit": "litro",
        "protein_per_100g": 3.0, "calories_per_100g": 61.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "yogur natural", "aliases": ["yogur", "yoghurt natural"],
        "category": "lacteo", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 5.0, "calories_per_100g": 59.0, "avg_shelf_life_days": 14,
    },
    {
        "name": "manteca", "aliases": ["mantequilla"],
        "category": "lacteo", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 1.0, "calories_per_100g": 717.0, "avg_shelf_life_days": 30,
    },
    {
        "name": "crema de leche", "aliases": ["crema", "nata"],
        "category": "lacteo", "storage_type": "refrigerado", "unit": "litro",
        "protein_per_100g": 2.0, "calories_per_100g": 345.0, "avg_shelf_life_days": 7,
    },
    {
        "name": "queso rallado", "aliases": ["parmesano", "queso duro rallado"],
        "category": "lacteo", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 36.0, "calories_per_100g": 392.0, "avg_shelf_life_days": 30,
    },
    {
        "name": "mozzarella", "aliases": ["mozarela", "queso mozzarella"],
        "category": "lacteo", "storage_type": "refrigerado", "unit": "kg",
        "protein_per_100g": 22.0, "calories_per_100g": 280.0, "avg_shelf_life_days": 7,
    },
    # ── CONDIMENTOS Y BÁSICOS (12) ───────────────────────────────────────────
    {
        "name": "aceite de oliva", "aliases": ["aceite oliva", "oliva"],
        "category": "condimento", "storage_type": "seco", "unit": "litro",
        "protein_per_100g": 0.0, "calories_per_100g": 884.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "sal", "aliases": ["sal fina", "sal gruesa"],
        "category": "condimento", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 0.0, "calories_per_100g": 0.0, "avg_shelf_life_days": 3650,
    },
    {
        "name": "ajo", "aliases": ["diente de ajo", "cabeza de ajo", "ajo fresco"],
        "category": "condimento", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 6.0, "calories_per_100g": 149.0, "avg_shelf_life_days": 30,
    },
    {
        "name": "oregano", "aliases": ["orégano", "oregano seco"],
        "category": "condimento", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 9.0, "calories_per_100g": 265.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "pimenton", "aliases": ["pimentón", "paprika", "pimenton dulce"],
        "category": "condimento", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 15.0, "calories_per_100g": 282.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "comino", "aliases": ["comino molido", "cumino"],
        "category": "condimento", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 18.0, "calories_per_100g": 375.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "pimienta negra", "aliases": ["pimienta", "pimienta molida"],
        "category": "condimento", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 10.0, "calories_per_100g": 251.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "aceite de girasol", "aliases": ["aceite vegetal", "girasol"],
        "category": "condimento", "storage_type": "seco", "unit": "litro",
        "protein_per_100g": 0.0, "calories_per_100g": 884.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "vinagre", "aliases": ["vinagre de alcohol", "vinagre de manzana"],
        "category": "condimento", "storage_type": "seco", "unit": "litro",
        "protein_per_100g": 0.0, "calories_per_100g": 22.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "salsa de tomate", "aliases": ["puré de tomate", "tomate triturado"],
        "category": "condimento", "storage_type": "seco", "unit": "unidad",
        "protein_per_100g": 2.0, "calories_per_100g": 35.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "caldo de pollo", "aliases": ["caldito", "pastilla de caldo"],
        "category": "condimento", "storage_type": "seco", "unit": "unidad",
        "protein_per_100g": 2.0, "calories_per_100g": 15.0, "avg_shelf_life_days": 365,
    },
    {
        "name": "laurel", "aliases": ["hoja de laurel", "laurel seco"],
        "category": "condimento", "storage_type": "seco", "unit": "kg",
        "protein_per_100g": 8.0, "calories_per_100g": 313.0, "avg_shelf_life_days": 365,
    },
]


async def seed_ingredients(session: AsyncSession) -> dict[str, int]:
    """Inserta ingredientes faltantes. Retorna mapa name → id."""
    # Cargar existentes
    result = await session.execute(select(IngredientORM))
    existing = {row.name: row.id for row in result.scalars()}

    created = 0
    for data in INGREDIENTS:
        if data["name"] in existing:
            continue
        orm = IngredientORM(
            name=data["name"],
            aliases=data["aliases"],
            category=data["category"],
            storage_type=data["storage_type"],
            unit=data["unit"],
            protein_per_100g=data["protein_per_100g"],
            calories_per_100g=data["calories_per_100g"],
            avg_shelf_life_days=data["avg_shelf_life_days"],
        )
        session.add(orm)
        created += 1

    await session.flush()

    # Recargar mapa con nuevos IDs
    result = await session.execute(select(IngredientORM))
    name_to_id = {row.name: row.id for row in result.scalars()}

    logger.info("Ingredientes: %d nuevos, %d ya existían", created, len(existing))
    return name_to_id


if __name__ == "__main__":
    async def _main():
        from app.config import get_settings
        from app.database import init_db, get_session
        settings = get_settings()
        init_db(settings.database_url)
        async with get_session() as session:
            await seed_ingredients(session)
            print("✅ Ingredientes cargados")

    asyncio.run(_main())
