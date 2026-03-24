"""
Seed de 16 recetas de Batch Cooking 1x5 para SGAI.
Todas aptas para refrigeración de 5 días (reheatable_days >= 3).
Ingredientes de supermercados de Recoleta, CABA, Argentina.
Idempotente: no duplica si ya existe por nombre.
"""

import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.ingredient_orm import IngredientORM
from app.adapters.persistence.recipe_ingredient_orm import RecipeIngredientORM
from app.adapters.persistence.recipe_orm import RecipeORM

logger = logging.getLogger(__name__)

# ── Datos ─────────────────────────────────────────────────────────────────────
# reheatable_days: 3-5 (todos batch-friendly)
# calories/protein/carbs/fat por porción (estimados)

RECIPES: list[dict] = [
    {
        "name": "Pollo al horno con vegetales",
        "description": "Pechuga de pollo con papa, batata y zanahoria al horno. Clásico del batch cooking.",
        "prep_time_minutes": 75,
        "is_batch_friendly": True,
        "reheatable_days": 5,
        "servings": 5,
        "calories_per_serving": 420.0,
        "protein_per_serving": 45.0,
        "carbs_per_serving": 35.0,
        "fat_per_serving": 10.0,
        "tags": ["alto_proteina", "sin_gluten", "bajo_costo"],
        "instructions": "1. Precalentar horno a 200°C. 2. Cortar papa, batata y zanahoria en cubos. 3. Salpimentar pechuga y marinar con ajo y aceite de oliva. 4. Distribuir todo en bandeja. 5. Hornear 50-60 min hasta dorar.",
        "ingredients": [
            {"name": "pechuga de pollo", "quantity": 1.5, "unit": "kg"},
            {"name": "papa", "quantity": 0.8, "unit": "kg"},
            {"name": "batata", "quantity": 0.5, "unit": "kg"},
            {"name": "zanahoria", "quantity": 0.4, "unit": "kg"},
            {"name": "aceite de oliva", "quantity": 0.05, "unit": "litro"},
            {"name": "ajo", "quantity": 0.02, "unit": "kg"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
            {"name": "pimienta negra", "quantity": 0.005, "unit": "kg"},
        ],
    },
    {
        "name": "Lentejas guisadas",
        "description": "Guiso de lentejas con cebolla, zanahoria y pimentón. Económico y alto en proteína vegetal.",
        "prep_time_minutes": 60,
        "is_batch_friendly": True,
        "reheatable_days": 5,
        "servings": 5,
        "calories_per_serving": 320.0,
        "protein_per_serving": 18.0,
        "carbs_per_serving": 50.0,
        "fat_per_serving": 5.0,
        "tags": ["vegetariano", "alto_proteina_vegetal", "muy_bajo_costo"],
        "instructions": "1. Remojar lentejas 2hs. 2. Rehogar cebolla y zanahoria en aceite. 3. Agregar pimentón y comino. 4. Incorporar lentejas escurridas. 5. Cubrir con agua y cocinar 35 min. 6. Añadir laurel y salpimentar.",
        "ingredients": [
            {"name": "lentejas", "quantity": 0.5, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.3, "unit": "kg"},
            {"name": "zanahoria", "quantity": 0.3, "unit": "kg"},
            {"name": "tomate", "quantity": 0.3, "unit": "kg"},
            {"name": "pimenton", "quantity": 0.01, "unit": "kg"},
            {"name": "comino", "quantity": 0.005, "unit": "kg"},
            {"name": "laurel", "quantity": 0.002, "unit": "kg"},
            {"name": "aceite de girasol", "quantity": 0.04, "unit": "litro"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
        ],
    },
    {
        "name": "Fideos con boloñesa de carne picada",
        "description": "Salsa boloñesa clásica con carne picada y tomate. Rendidora y recalentable.",
        "prep_time_minutes": 60,
        "is_batch_friendly": True,
        "reheatable_days": 4,
        "servings": 5,
        "calories_per_serving": 480.0,
        "protein_per_serving": 32.0,
        "carbs_per_serving": 55.0,
        "fat_per_serving": 14.0,
        "tags": ["clasico", "alto_proteina"],
        "instructions": "1. Rehogar cebolla y ajo en aceite. 2. Dorar carne picada. 3. Agregar tomate triturado y salsa de tomate. 4. Condimentar con orégano y laurel. 5. Cocinar 30 min. 6. Hervir fideos al dente por separado.",
        "ingredients": [
            {"name": "carne picada", "quantity": 0.8, "unit": "kg"},
            {"name": "fideos", "quantity": 0.5, "unit": "kg"},
            {"name": "tomate", "quantity": 0.4, "unit": "kg"},
            {"name": "salsa de tomate", "quantity": 2.0, "unit": "unidad"},
            {"name": "cebolla", "quantity": 0.2, "unit": "kg"},
            {"name": "ajo", "quantity": 0.02, "unit": "kg"},
            {"name": "oregano", "quantity": 0.005, "unit": "kg"},
            {"name": "laurel", "quantity": 0.002, "unit": "kg"},
            {"name": "aceite de girasol", "quantity": 0.04, "unit": "litro"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
        ],
    },
    {
        "name": "Guiso de garbanzos con verduras",
        "description": "Garbanzos con papa, zanahoria y morron. Sustancioso y apto para toda la semana.",
        "prep_time_minutes": 75,
        "is_batch_friendly": True,
        "reheatable_days": 5,
        "servings": 5,
        "calories_per_serving": 350.0,
        "protein_per_serving": 15.0,
        "carbs_per_serving": 55.0,
        "fat_per_serving": 6.0,
        "tags": ["vegetariano", "sin_gluten", "alto_proteina_vegetal"],
        "instructions": "1. Remojar garbanzos overnight. 2. Rehogar cebolla y morron. 3. Agregar papa y zanahoria cubeteadas. 4. Incorporar garbanzos. 5. Condimentar con pimentón y comino. 6. Cocinar 45 min con agua.",
        "ingredients": [
            {"name": "garbanzos", "quantity": 0.4, "unit": "kg"},
            {"name": "papa", "quantity": 0.5, "unit": "kg"},
            {"name": "zanahoria", "quantity": 0.3, "unit": "kg"},
            {"name": "morron rojo", "quantity": 0.3, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.2, "unit": "kg"},
            {"name": "tomate", "quantity": 0.3, "unit": "kg"},
            {"name": "pimenton", "quantity": 0.01, "unit": "kg"},
            {"name": "comino", "quantity": 0.005, "unit": "kg"},
            {"name": "aceite de girasol", "quantity": 0.04, "unit": "litro"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
        ],
    },
    {
        "name": "Arroz con pollo",
        "description": "Muslos de pollo cocinados con arroz, caldo y vegetales. Receta completa en una olla.",
        "prep_time_minutes": 60,
        "is_batch_friendly": True,
        "reheatable_days": 4,
        "servings": 5,
        "calories_per_serving": 445.0,
        "protein_per_serving": 35.0,
        "carbs_per_serving": 48.0,
        "fat_per_serving": 12.0,
        "tags": ["clasico", "alto_proteina", "una_olla"],
        "instructions": "1. Dorar muslos de pollo. 2. Rehogar cebolla, morron y ajo. 3. Agregar arroz lavado. 4. Cubrir con caldo de pollo caliente. 5. Cocinar tapado 20 min a fuego bajo. 6. Reposar 10 min.",
        "ingredients": [
            {"name": "muslo de pollo", "quantity": 1.2, "unit": "kg"},
            {"name": "arroz", "quantity": 0.4, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.2, "unit": "kg"},
            {"name": "morron rojo", "quantity": 0.2, "unit": "kg"},
            {"name": "tomate", "quantity": 0.3, "unit": "kg"},
            {"name": "caldo de pollo", "quantity": 2.0, "unit": "unidad"},
            {"name": "ajo", "quantity": 0.015, "unit": "kg"},
            {"name": "pimenton", "quantity": 0.008, "unit": "kg"},
            {"name": "aceite de girasol", "quantity": 0.04, "unit": "litro"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
        ],
    },
    {
        "name": "Merluza al horno con papa",
        "description": "Filetes de merluza sobre cama de papas al horno con cebolla y limón. Liviano y proteico.",
        "prep_time_minutes": 50,
        "is_batch_friendly": True,
        "reheatable_days": 3,
        "servings": 5,
        "calories_per_serving": 280.0,
        "protein_per_serving": 30.0,
        "carbs_per_serving": 25.0,
        "fat_per_serving": 7.0,
        "tags": ["pescado", "sin_gluten", "bajo_calorias"],
        "instructions": "1. Precalentar horno a 180°C. 2. Cortar papas en rodajas finas. 3. Disponer papas en fuente con aceite y cebolla. 4. Colocar filetes de merluza encima. 5. Condimentar con sal, pimienta y orégano. 6. Hornear 30-35 min.",
        "ingredients": [
            {"name": "merluza", "quantity": 1.0, "unit": "kg"},
            {"name": "papa", "quantity": 0.8, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.2, "unit": "kg"},
            {"name": "aceite de oliva", "quantity": 0.05, "unit": "litro"},
            {"name": "oregano", "quantity": 0.005, "unit": "kg"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
            {"name": "pimienta negra", "quantity": 0.003, "unit": "kg"},
            {"name": "vinagre", "quantity": 0.02, "unit": "litro"},
        ],
    },
    {
        "name": "Milanesas de soja texturizada",
        "description": "Milanesas veganas de soja texturizada, rebozadas con harina. Económicas y proteicas.",
        "prep_time_minutes": 45,
        "is_batch_friendly": True,
        "reheatable_days": 4,
        "servings": 5,
        "calories_per_serving": 310.0,
        "protein_per_serving": 28.0,
        "carbs_per_serving": 30.0,
        "fat_per_serving": 8.0,
        "tags": ["vegetariano", "alto_proteina_vegetal", "muy_bajo_costo"],
        "instructions": "1. Hidratar soja texturizada en agua caliente 20 min. 2. Escurrir y condimentar con sal, pimentón, ajo. 3. Pasar por harina de trigo y huevo batido. 4. Freír en aceite caliente o hornear a 200°C 20 min. 5. Servir con ensalada.",
        "ingredients": [
            {"name": "soja texturizada", "quantity": 0.3, "unit": "kg"},
            {"name": "huevo", "quantity": 3.0, "unit": "unidad"},
            {"name": "harina de trigo", "quantity": 0.2, "unit": "kg"},
            {"name": "pimenton", "quantity": 0.01, "unit": "kg"},
            {"name": "ajo", "quantity": 0.01, "unit": "kg"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
            {"name": "aceite de girasol", "quantity": 0.1, "unit": "litro"},
        ],
    },
    {
        "name": "Porotos negros guisados",
        "description": "Guiso reconfortante de porotos negros con cebolla, zanahoria y especias. Muy económico.",
        "prep_time_minutes": 90,
        "is_batch_friendly": True,
        "reheatable_days": 5,
        "servings": 5,
        "calories_per_serving": 280.0,
        "protein_per_serving": 14.0,
        "carbs_per_serving": 45.0,
        "fat_per_serving": 5.0,
        "tags": ["vegetariano", "muy_bajo_costo", "alto_proteina_vegetal"],
        "instructions": "1. Remojar porotos overnight. 2. Rehogar cebolla y zanahoria. 3. Agregar tomate. 4. Incorporar porotos escurridos. 5. Condimentar con pimentón, comino y laurel. 6. Cocinar 60 min. 7. Ajustar sal al final.",
        "ingredients": [
            {"name": "porotos negros", "quantity": 0.4, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.3, "unit": "kg"},
            {"name": "zanahoria", "quantity": 0.3, "unit": "kg"},
            {"name": "tomate", "quantity": 0.3, "unit": "kg"},
            {"name": "pimenton", "quantity": 0.01, "unit": "kg"},
            {"name": "comino", "quantity": 0.005, "unit": "kg"},
            {"name": "laurel", "quantity": 0.002, "unit": "kg"},
            {"name": "aceite de girasol", "quantity": 0.04, "unit": "litro"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
        ],
    },
    {
        "name": "Revuelto de espinaca con huevo",
        "description": "Huevos revueltos con espinaca fresca y cebolla de verdeo. Rápido y nutritivo.",
        "prep_time_minutes": 20,
        "is_batch_friendly": True,
        "reheatable_days": 3,
        "servings": 3,
        "calories_per_serving": 200.0,
        "protein_per_serving": 16.0,
        "carbs_per_serving": 5.0,
        "fat_per_serving": 12.0,
        "tags": ["rapido", "sin_gluten", "desayuno_proteico"],
        "instructions": "1. Saltear cebolla de verdeo en aceite. 2. Agregar espinaca y cocinar hasta marchitar. 3. Batir huevos con sal y pimienta. 4. Incorporar huevos a la sartén. 5. Revolver suavemente hasta cuajar. 6. Servir caliente.",
        "ingredients": [
            {"name": "huevo", "quantity": 8.0, "unit": "unidad"},
            {"name": "espinaca", "quantity": 0.3, "unit": "kg"},
            {"name": "cebolla de verdeo", "quantity": 0.1, "unit": "kg"},
            {"name": "aceite de oliva", "quantity": 0.03, "unit": "litro"},
            {"name": "sal", "quantity": 0.005, "unit": "kg"},
            {"name": "pimienta negra", "quantity": 0.002, "unit": "kg"},
        ],
    },
    {
        "name": "Polenta con salsa de tomate y queso",
        "description": "Polenta cremosa con salsa de tomate casera y queso rallado. Comfort food económico.",
        "prep_time_minutes": 35,
        "is_batch_friendly": True,
        "reheatable_days": 4,
        "servings": 4,
        "calories_per_serving": 380.0,
        "protein_per_serving": 14.0,
        "carbs_per_serving": 58.0,
        "fat_per_serving": 10.0,
        "tags": ["vegetariano", "bajo_costo", "reconfortante"],
        "instructions": "1. Hervir 1L agua con sal. 2. Agregar polenta en lluvia revolviendo. 3. Cocinar 15 min revolviendo. 4. Incorporar manteca y queso rallado. 5. Calentar salsa de tomate con ajo y orégano. 6. Servir polenta con salsa.",
        "ingredients": [
            {"name": "polenta", "quantity": 0.4, "unit": "kg"},
            {"name": "salsa de tomate", "quantity": 2.0, "unit": "unidad"},
            {"name": "queso rallado", "quantity": 0.1, "unit": "kg"},
            {"name": "manteca", "quantity": 0.03, "unit": "kg"},
            {"name": "ajo", "quantity": 0.01, "unit": "kg"},
            {"name": "oregano", "quantity": 0.005, "unit": "kg"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
        ],
    },
    {
        "name": "Tarta de verduras con ricota",
        "description": "Tarta de espinaca, zapallito y cebolla con base de harina. Clásico porteño.",
        "prep_time_minutes": 70,
        "is_batch_friendly": True,
        "reheatable_days": 4,
        "servings": 6,
        "calories_per_serving": 290.0,
        "protein_per_serving": 14.0,
        "carbs_per_serving": 28.0,
        "fat_per_serving": 12.0,
        "tags": ["vegetariano", "clasico_porteno"],
        "instructions": "1. Hacer masa: harina, manteca, sal y agua fría. 2. Blanquear espinaca y zapallito. 3. Mezclar verduras con ricota, huevos y condimentos. 4. Forrar molde con masa. 5. Rellenar y hornear 40 min a 180°C.",
        "ingredients": [
            {"name": "harina de trigo", "quantity": 0.3, "unit": "kg"},
            {"name": "manteca", "quantity": 0.08, "unit": "kg"},
            {"name": "espinaca", "quantity": 0.4, "unit": "kg"},
            {"name": "zapallito", "quantity": 0.3, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.2, "unit": "kg"},
            {"name": "ricota", "quantity": 0.3, "unit": "kg"},
            {"name": "huevo", "quantity": 3.0, "unit": "unidad"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
            {"name": "pimienta negra", "quantity": 0.003, "unit": "kg"},
        ],
    },
    {
        "name": "Muslos de pollo al horno con batata",
        "description": "Muslos jugosos con batata caramelizada. Fácil, económico y delicioso.",
        "prep_time_minutes": 65,
        "is_batch_friendly": True,
        "reheatable_days": 5,
        "servings": 5,
        "calories_per_serving": 410.0,
        "protein_per_serving": 35.0,
        "carbs_per_serving": 30.0,
        "fat_per_serving": 15.0,
        "tags": ["alto_proteina", "sin_gluten", "simple"],
        "instructions": "1. Precalentar horno a 200°C. 2. Marinar muslos con ajo, pimentón, aceite y sal. 3. Cortar batata en gajos. 4. Disponer todo en asadera. 5. Hornear 50 min dando vuelta a mitad. 6. Gratinar 5 min.",
        "ingredients": [
            {"name": "muslo de pollo", "quantity": 1.3, "unit": "kg"},
            {"name": "batata", "quantity": 0.7, "unit": "kg"},
            {"name": "ajo", "quantity": 0.02, "unit": "kg"},
            {"name": "pimenton", "quantity": 0.01, "unit": "kg"},
            {"name": "aceite de oliva", "quantity": 0.05, "unit": "litro"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
            {"name": "pimienta negra", "quantity": 0.003, "unit": "kg"},
        ],
    },
    {
        "name": "Guiso de cerdo con papa",
        "description": "Estofado de bondiola de cerdo con papa, zanahoria y vino blanco. Sabroso y rendidor.",
        "prep_time_minutes": 90,
        "is_batch_friendly": True,
        "reheatable_days": 5,
        "servings": 5,
        "calories_per_serving": 450.0,
        "protein_per_serving": 30.0,
        "carbs_per_serving": 28.0,
        "fat_per_serving": 18.0,
        "tags": ["cerdo", "sin_gluten", "estofado"],
        "instructions": "1. Cortar bondiola en cubos. 2. Dorar en aceite caliente. 3. Agregar cebolla, zanahoria y tomate. 4. Añadir papa cubeteada. 5. Condimentar con pimentón, laurel y comino. 6. Cubrir con agua y cocinar 60 min a fuego bajo.",
        "ingredients": [
            {"name": "cerdo bondiola", "quantity": 1.0, "unit": "kg"},
            {"name": "papa", "quantity": 0.6, "unit": "kg"},
            {"name": "zanahoria", "quantity": 0.3, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.2, "unit": "kg"},
            {"name": "tomate", "quantity": 0.3, "unit": "kg"},
            {"name": "pimenton", "quantity": 0.01, "unit": "kg"},
            {"name": "comino", "quantity": 0.005, "unit": "kg"},
            {"name": "laurel", "quantity": 0.002, "unit": "kg"},
            {"name": "aceite de girasol", "quantity": 0.04, "unit": "litro"},
            {"name": "sal", "quantity": 0.01, "unit": "kg"},
        ],
    },
    {
        "name": "Atun con arroz y morron",
        "description": "Arroz salteado con atún en lata, morrón y cebolla. Rápido, proteico y muy económico.",
        "prep_time_minutes": 30,
        "is_batch_friendly": True,
        "reheatable_days": 3,
        "servings": 4,
        "calories_per_serving": 380.0,
        "protein_per_serving": 28.0,
        "carbs_per_serving": 45.0,
        "fat_per_serving": 9.0,
        "tags": ["rapido", "pescado", "bajo_costo", "alto_proteina"],
        "instructions": "1. Cocinar arroz. 2. Saltear cebolla y morron en aceite. 3. Agregar atún escurrido. 4. Incorporar arroz cocido y mezclar. 5. Condimentar con sal, pimienta y orégano. 6. Servir caliente.",
        "ingredients": [
            {"name": "atun en lata", "quantity": 3.0, "unit": "unidad"},
            {"name": "arroz", "quantity": 0.4, "unit": "kg"},
            {"name": "morron rojo", "quantity": 0.3, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.2, "unit": "kg"},
            {"name": "aceite de girasol", "quantity": 0.04, "unit": "litro"},
            {"name": "sal", "quantity": 0.008, "unit": "kg"},
            {"name": "oregano", "quantity": 0.005, "unit": "kg"},
            {"name": "pimienta negra", "quantity": 0.002, "unit": "kg"},
        ],
    },
    {
        "name": "Fideos integrales con pesto de espinaca",
        "description": "Fideos integrales con pesto de espinaca, ajo y queso rallado. Saludable y sabroso.",
        "prep_time_minutes": 25,
        "is_batch_friendly": True,
        "reheatable_days": 3,
        "servings": 4,
        "calories_per_serving": 420.0,
        "protein_per_serving": 18.0,
        "carbs_per_serving": 60.0,
        "fat_per_serving": 14.0,
        "tags": ["vegetariano", "rapido", "integral"],
        "instructions": "1. Hervir fideos integrales al dente. 2. Blanquear espinaca. 3. Procesar espinaca con ajo, aceite de oliva, sal y queso rallado. 4. Escurrir fideos reservando agua de cocción. 5. Mezclar con pesto, agregar agua si necesita.",
        "ingredients": [
            {"name": "fideos integrales", "quantity": 0.5, "unit": "kg"},
            {"name": "espinaca", "quantity": 0.3, "unit": "kg"},
            {"name": "ajo", "quantity": 0.02, "unit": "kg"},
            {"name": "aceite de oliva", "quantity": 0.06, "unit": "litro"},
            {"name": "queso rallado", "quantity": 0.08, "unit": "kg"},
            {"name": "sal", "quantity": 0.008, "unit": "kg"},
            {"name": "pimienta negra", "quantity": 0.002, "unit": "kg"},
        ],
    },
    {
        "name": "Garbanzos salteados con verduras",
        "description": "Garbanzos cocidos salteados con zapallito, morrón y cebolla. Rápido si se usan de lata.",
        "prep_time_minutes": 30,
        "is_batch_friendly": True,
        "reheatable_days": 4,
        "servings": 4,
        "calories_per_serving": 290.0,
        "protein_per_serving": 13.0,
        "carbs_per_serving": 40.0,
        "fat_per_serving": 8.0,
        "tags": ["vegetariano", "rapido", "sin_gluten", "alto_proteina_vegetal"],
        "instructions": "1. Cocinar garbanzos (o usar de lata escurridos). 2. Saltear cebolla en aceite caliente. 3. Agregar morron y zapallito. 4. Incorporar garbanzos. 5. Condimentar con pimentón, comino y sal. 6. Saltear 5 min a fuego alto.",
        "ingredients": [
            {"name": "garbanzos", "quantity": 0.35, "unit": "kg"},
            {"name": "zapallito", "quantity": 0.3, "unit": "kg"},
            {"name": "morron rojo", "quantity": 0.2, "unit": "kg"},
            {"name": "cebolla", "quantity": 0.2, "unit": "kg"},
            {"name": "pimenton", "quantity": 0.008, "unit": "kg"},
            {"name": "comino", "quantity": 0.004, "unit": "kg"},
            {"name": "aceite de oliva", "quantity": 0.04, "unit": "litro"},
            {"name": "sal", "quantity": 0.008, "unit": "kg"},
        ],
    },
]


async def seed_recipes(session: AsyncSession, name_to_id: dict[str, int]) -> None:
    """Inserta recetas faltantes con sus ingredientes."""
    # Cargar recetas existentes por nombre
    result = await session.execute(select(RecipeORM))
    existing_names = {row.name for row in result.scalars()}

    created = 0
    warnings = 0

    for data in RECIPES:
        if data["name"] in existing_names:
            continue

        recipe_orm = RecipeORM(
            name=data["name"],
            description=data["description"],
            prep_time_minutes=data["prep_time_minutes"],
            is_batch_friendly=data["is_batch_friendly"],
            reheatable_days=data["reheatable_days"],
            servings=data["servings"],
            calories_per_serving=data["calories_per_serving"],
            protein_per_serving=data["protein_per_serving"],
            carbs_per_serving=data["carbs_per_serving"],
            fat_per_serving=data["fat_per_serving"],
            instructions=data["instructions"],
            tags=data["tags"],
        )
        session.add(recipe_orm)
        await session.flush()

        for ing_data in data["ingredients"]:
            ing_id = name_to_id.get(ing_data["name"])
            if ing_id is None:
                logger.warning(
                    "Receta '%s': ingrediente '%s' no encontrado en DB",
                    data["name"], ing_data["name"],
                )
                warnings += 1
                continue
            ri = RecipeIngredientORM(
                recipe_id=recipe_orm.id,
                ingredient_id=ing_id,
                quantity_amount=ing_data["quantity"],
                unit=ing_data["unit"],
            )
            session.add(ri)

        await session.flush()
        created += 1

    logger.info("Recetas: %d nuevas, %d ya existían, %d advertencias de ingredientes",
                created, len(existing_names), warnings)


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
            await seed_recipes(session, name_to_id)
            print("✅ Recetas cargadas")

    asyncio.run(_main())
