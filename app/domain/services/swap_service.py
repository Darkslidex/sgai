"""
Swap Service — Quick Swap con Matriz de Eficiencia Nutricional (ADR-008).

Sugiere sustitutos de ingredientes priorizando costo/gramo de proteína.
No requiere IA: opera puramente sobre datos de la DB.
"""

import logging
from dataclasses import dataclass

from app.domain.models.ingredient import Ingredient
from app.domain.models.market import MarketPrice
from app.domain.ports.ingredient_repository import IngredientRepositoryPort
from app.domain.ports.market_repository import MarketRepositoryPort

logger = logging.getLogger(__name__)


@dataclass
class SwapSuggestion:
    """Un sustituto sugerido con su puntuación de eficiencia nutricional."""

    ingredient: Ingredient
    current_price_ars: float
    protein_per_100g: float
    efficiency_score: float   # ADR-008: normalizado 0-100
    cost_delta_ars: float     # positivo = más caro, negativo = más barato
    protein_delta_g: float    # positivo = más proteína, negativo = menos
    reason: str


def calculate_efficiency_score(ingredient: Ingredient, price: MarketPrice) -> float:
    """
    ADR-008: Matriz de Eficiencia Nutricional.

    Calcula qué tan eficiente es un ingrediente en proteína por peso argentino gastado.
    Fórmula: (protein_per_100g / price_per_100g_ars) * 100

    Ejemplos reales Argentina:
    - Lentejas:   ~9g prot / ~$80/100g  = score 11.25 (ÓPTIMO)
    - Huevo:     ~13g prot / ~$150/100g = score  8.67 (EXCELENTE)
    - Pollo:     ~27g prot / ~$400/100g = score  6.75 (BUENO)
    - Carne vacuna: ~26g / ~$800/100g  = score  3.25 (CARO)
    """
    if not ingredient.protein_per_100g or ingredient.protein_per_100g <= 0:
        return 0.0
    if price.price_ars <= 0:
        return 0.0
    return (ingredient.protein_per_100g / price.price_ars) * 100


def _normalize_scores(scores: list[float]) -> list[float]:
    """Normaliza una lista de scores al rango 0-100."""
    if not scores:
        return []
    max_s = max(scores)
    if max_s == 0:
        return [0.0] * len(scores)
    return [(s / max_s) * 100 for s in scores]


class SwapService:
    """
    Quick Swap inteligente con Matriz de Eficiencia Nutricional (ADR-008).

    Busca ingredientes de la misma categoría, calcula eficiencia costo/proteína
    y retorna los top 3 sustitutos rankeados.
    """

    def __init__(
        self,
        ingredient_repo: IngredientRepositoryPort,
        market_repo: MarketRepositoryPort,
    ) -> None:
        self._ingredient_repo = ingredient_repo
        self._market_repo = market_repo

    async def suggest_swap(
        self,
        ingredient_id: int,
        reason: str = "unavailable",
    ) -> list[SwapSuggestion]:
        """
        Sugiere hasta 3 sustitutos para un ingrediente.

        Args:
            ingredient_id: ID del ingrediente a reemplazar.
            reason: Motivo del swap ("unavailable", "too_expensive", "preference").

        Returns:
            Lista ordenada por efficiency_score descendente (top 3).
        """
        # 1. Obtener ingrediente original
        original = await self._ingredient_repo.get_ingredient(ingredient_id)
        if original is None:
            logger.warning("Ingrediente %d no encontrado para swap", ingredient_id)
            return []

        original_price = await self._market_repo.get_current_price(ingredient_id)

        # 2. Obtener todos los ingredientes de la misma categoría
        all_ingredients = await self._ingredient_repo.list_ingredients()
        candidates = [
            ing for ing in all_ingredients
            if ing.category == original.category and ing.id != ingredient_id
        ]

        if not candidates:
            logger.info("Sin candidatos de categoría '%s' para swap", original.category)
            return []

        # 3. Obtener precios actuales para los candidatos
        all_prices = await self._market_repo.get_all_current_prices()
        price_map = {p.ingredient_id: p for p in all_prices}

        # Filtrar candidatos que tengan precio disponible
        priced_candidates = [
            (ing, price_map[ing.id])
            for ing in candidates
            if ing.id in price_map
        ]

        if not priced_candidates:
            return []

        # 4. Calcular Matriz de Eficiencia Nutricional (ADR-008)
        raw_scores = [calculate_efficiency_score(ing, price) for ing, price in priced_candidates]
        normalized = _normalize_scores(raw_scores)

        # 5. Construir sugerencias con deltas
        original_protein = original.protein_per_100g or 0.0
        original_price_ars = original_price.price_ars if original_price else 0.0

        suggestions: list[SwapSuggestion] = []
        for (ing, price), norm_score in zip(priced_candidates, normalized):
            protein = ing.protein_per_100g or 0.0
            cost_delta = price.price_ars - original_price_ars
            protein_delta = protein - original_protein

            # Generar razón legible
            if norm_score >= 70:
                reason_text = f"Alta eficiencia proteica (score {norm_score:.0f}/100)"
            elif cost_delta < 0:
                reason_text = f"Más económico ({abs(cost_delta):.0f} ARS menos)"
            else:
                reason_text = f"Misma categoría ({ing.category})"

            suggestions.append(
                SwapSuggestion(
                    ingredient=ing,
                    current_price_ars=price.price_ars,
                    protein_per_100g=protein,
                    efficiency_score=norm_score,
                    cost_delta_ars=cost_delta,
                    protein_delta_g=protein_delta,
                    reason=reason_text,
                )
            )

        # 6. Rankear por efficiency_score descendente, retornar top 3
        suggestions.sort(key=lambda s: s.efficiency_score, reverse=True)
        return suggestions[:3]

    async def get_efficiency_ranking(self, limit: int = 10) -> list[tuple[Ingredient, float, float]]:
        """
        Ranking de todos los ingredientes por efficiency_score (ADR-008).

        Returns:
            Lista de (ingredient, efficiency_score_raw, price_ars) ordenada desc.
        """
        all_ingredients = await self._ingredient_repo.list_ingredients()
        all_prices = await self._market_repo.get_all_current_prices()
        price_map = {p.ingredient_id: p for p in all_prices}

        scored = []
        for ing in all_ingredients:
            if ing.id in price_map and (ing.protein_per_100g or 0) > 0:
                score = calculate_efficiency_score(ing, price_map[ing.id])
                scored.append((ing, score, price_map[ing.id].price_ars))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]
