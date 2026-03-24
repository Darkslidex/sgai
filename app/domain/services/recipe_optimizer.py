"""
Servicio de optimización de recetas por solapamiento de ingredientes.

Encuentra la combinación de N recetas que:
1. Maximiza solapamiento de ingredientes (menos items a comprar)
2. Respeta presupuesto máximo
3. Cumple score mínimo de recalentabilidad
4. Incluye tags requeridas

Ranking: overlap_score * 0.6 + (1 - costo_normalizado) * 0.4
"""

import logging
from itertools import combinations

from app.domain.models.pantry_item import PantryItem
from app.domain.models.recipe import Recipe
from app.domain.models.recipe_ingredient import RecipeIngredient
from app.domain.ports.market_repository import MarketRepositoryPort
from app.domain.ports.recipe_repository import RecipeRepositoryPort

logger = logging.getLogger(__name__)


class RecipeOptimizer:
    def __init__(
        self,
        recipe_repo: RecipeRepositoryPort,
        market_repo: MarketRepositoryPort,
    ) -> None:
        self._recipe_repo = recipe_repo
        self._market_repo = market_repo

    async def find_optimal_combination(
        self,
        num_recipes: int = 3,
        max_budget_ars: float | None = None,
        min_reheatable: int = 3,
        required_tags: list[str] | None = None,
    ) -> list[dict]:
        """
        Encuentra las mejores combinaciones de N recetas por solapamiento.

        Returns:
            Lista de hasta 3 dicts con:
            - recipes: list[Recipe]
            - unique_ingredients: int
            - shared_ingredients: int
            - overlap_score: float (0-1)
            - estimated_cost_ars: float
            - combined_tags: list[str]
        """
        # 1. Filtrar recetas por criterios
        all_recipes = await self._recipe_repo.list_recipes(
            filters={"min_reheatable_days": min_reheatable, "is_batch_friendly": True}
        )

        if required_tags:
            all_recipes = [
                r for r in all_recipes
                if any(tag in (r.tags or []) for tag in required_tags)
            ]

        if len(all_recipes) < num_recipes:
            logger.warning(
                "Solo hay %d recetas disponibles para combinar %d",
                len(all_recipes), num_recipes,
            )
            num_recipes = max(1, len(all_recipes))

        # 2. Pre-cargar ingredientes de todas las recetas
        recipe_ingredients: dict[int, list[RecipeIngredient]] = {}
        for recipe in all_recipes:
            recipe_ingredients[recipe.id] = await self._recipe_repo.get_recipe_ingredients(recipe.id)

        # 3. Pre-cargar precios
        all_prices = await self._market_repo.get_all_current_prices()
        price_map = {p.ingredient_id: p.price_ars for p in all_prices}

        # 4. Evaluar todas las combinaciones
        scored: list[tuple[float, dict]] = []

        for combo in combinations(all_recipes, num_recipes):
            result = _evaluate_combination(list(combo), recipe_ingredients, price_map)

            # Filtrar por presupuesto
            if max_budget_ars is not None and result["estimated_cost_ars"] > max_budget_ars:
                continue

            scored.append((result["_score"], result))

        if not scored:
            return []

        # 5. Normalizar costos y recalcular score final
        max_cost = max(r["estimated_cost_ars"] for _, r in scored) or 1.0
        final: list[tuple[float, dict]] = []
        for _, result in scored:
            norm_cost = result["estimated_cost_ars"] / max_cost
            final_score = result["overlap_score"] * 0.6 + (1 - norm_cost) * 0.4
            result.pop("_score", None)
            final.append((final_score, result))

        final.sort(key=lambda x: x[0], reverse=True)

        return [result for _, result in final[:3]]

    async def calculate_shopping_list(
        self,
        recipes: list[Recipe],
        pantry: list[PantryItem],
    ) -> list[dict]:
        """
        Genera lista de compras descontando lo que hay en pantry.

        Returns:
            Lista de dicts con: ingredient_name, needed, in_pantry, to_buy,
            unit, estimated_cost_ars, best_source
        """
        # Sumar cantidades necesarias por ingrediente
        needed: dict[int, tuple[float, str]] = {}  # id → (total_qty, unit)
        ing_names: dict[int, str] = {}

        for recipe in recipes:
            ris = await self._recipe_repo.get_recipe_ingredients(recipe.id)
            for ri in ris:
                if ri.ingredient_id not in needed:
                    needed[ri.ingredient_id] = (0.0, ri.unit)
                prev_qty, unit = needed[ri.ingredient_id]
                needed[ri.ingredient_id] = (prev_qty + ri.quantity_amount, unit)

        # Cargar nombres de ingredientes
        all_prices = await self._market_repo.get_all_current_prices()
        price_map = {p.ingredient_id: (p.price_ars, p.source) for p in all_prices}

        # Construir mapa pantry (ingredient_id → quantity)
        pantry_map: dict[int, float] = {}
        for item in pantry:
            pantry_map[item.ingredient_id] = pantry_map.get(item.ingredient_id, 0.0) + item.quantity_amount

        shopping_list = []
        for ing_id, (total_qty, unit) in needed.items():
            in_pantry = pantry_map.get(ing_id, 0.0)
            to_buy = max(0.0, total_qty - in_pantry)

            price_ars, source = price_map.get(ing_id, (0.0, "unknown"))
            cost = to_buy * price_ars if price_ars > 0 else 0.0

            shopping_list.append({
                "ingredient_id": ing_id,
                "needed": round(total_qty, 3),
                "in_pantry": round(in_pantry, 3),
                "to_buy": round(to_buy, 3),
                "unit": unit,
                "estimated_cost_ars": round(cost, 2),
                "best_source": source,
            })

        # Ordenar por costo descendente (los más caros primero)
        shopping_list.sort(key=lambda x: x["estimated_cost_ars"], reverse=True)
        return shopping_list


# ── Helpers ───────────────────────────────────────────────────────────────────

def _evaluate_combination(
    recipes: list[Recipe],
    recipe_ingredients: dict[int, list[RecipeIngredient]],
    price_map: dict[int, float],
) -> dict:
    """Evalúa una combinación de recetas: solapamiento y costo estimado."""
    # Ingredientes por receta
    sets: list[set[int]] = []
    for recipe in recipes:
        ids = {ri.ingredient_id for ri in recipe_ingredients.get(recipe.id, [])}
        sets.append(ids)

    all_ids: set[int] = set().union(*sets)
    unique_count = len(all_ids)

    # Ingredientes compartidos (aparecen en 2+ recetas)
    shared: set[int] = set()
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            shared |= sets[i] & sets[j]
    shared_count = len(shared)

    overlap_score = shared_count / unique_count if unique_count > 0 else 0.0

    # Costo estimado (suma de precios de ingredientes únicos necesarios)
    estimated_cost = sum(price_map.get(ing_id, 0.0) for ing_id in all_ids)

    # Tags combinadas
    combined_tags: list[str] = []
    for recipe in recipes:
        for tag in (recipe.tags or []):
            if tag not in combined_tags:
                combined_tags.append(tag)

    return {
        "recipes": recipes,
        "unique_ingredients": unique_count,
        "shared_ingredients": shared_count,
        "overlap_score": round(overlap_score, 4),
        "estimated_cost_ars": round(estimated_cost, 2),
        "combined_tags": combined_tags,
        "_score": overlap_score,  # se reemplaza en el ranking final
    }
