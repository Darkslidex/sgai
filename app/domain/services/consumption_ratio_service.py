"""
Servicio de Ratio Consumo/Vencimiento — ADR-008.

Cruza datos entre la cantidad comprada y la velocidad de consumo histórico
para evitar sugerencias de stock que superen la fecha de caducidad.

Previene desperdicio: si comprás 2kg de pollo pero solo consumís 500g/semana,
el sistema avisa que vas a desperdiciar antes del vencimiento.
"""

import logging
from dataclasses import dataclass

from app.domain.models.pantry_item import PantryItem
from app.domain.ports.ingredient_repository import IngredientRepositoryPort
from app.domain.ports.market_repository import MarketRepositoryPort
from app.domain.ports.planning_repository import PlanningRepositoryPort

logger = logging.getLogger(__name__)

_HISTORY_WEEKS = 8          # Semanas a considerar para el promedio
_MIN_DATA_POINTS = 2        # Mínimo para usar datos históricos
_SAFETY_FACTOR = 0.9        # Factor de seguridad en la cantidad ajustada
_FULL_CONFIDENCE_WEEKS = 8  # Semanas para confidence = 1.0


@dataclass
class ConsumptionRate:
    """Velocidad de consumo histórico de un ingrediente."""
    ingredient_id: int
    avg_weekly_consumption: float   # gramos o unidades por semana
    data_points: int                # semanas de datos
    confidence: float               # 0.0–1.0
    source: str                     # "historical" o "estimated"


@dataclass
class PurchaseValidation:
    """Resultado de validar una sugerencia de compra contra el ratio consumo/vencimiento."""
    is_valid: bool
    original_quantity: float
    suggested_quantity_adjusted: float | None
    days_to_consume: float
    shelf_life_days: int
    waste_risk_percentage: float
    message: str


@dataclass
class WasteRiskItem:
    """Item del pantry con evaluación de riesgo de desperdicio."""
    pantry_item: PantryItem
    days_remaining: int
    days_to_consume: float
    waste_risk: float   # 0.0–1.0
    action: str         # "ok" | "consume_soon" | "will_waste"


class ConsumptionRatioService:
    """ADR-008: Ratio Consumo/Vencimiento.

    Calcula la velocidad de consumo histórico de cada ingrediente cruzando
    los planes semanales anteriores. Valida cantidades de compra contra la
    vida útil del producto para prevenir desperdicio.
    """

    def __init__(
        self,
        market_repo: MarketRepositoryPort,
        planning_repo: PlanningRepositoryPort,
        ingredient_repo: IngredientRepositoryPort,
    ) -> None:
        self._market_repo = market_repo
        self._planning_repo = planning_repo
        self._ingredient_repo = ingredient_repo

    async def calculate_consumption_rate(
        self,
        user_id: int,
        ingredient_id: int,
    ) -> ConsumptionRate:
        """Calcula la velocidad de consumo histórico de un ingrediente.

        Algoritmo:
        1. Obtiene los últimos _HISTORY_WEEKS planes semanales.
        2. Para cada plan, busca el ingrediente en la shopping_list_json.
        3. Promedia las cantidades semanales encontradas.
        4. Si hay < _MIN_DATA_POINTS semanas, usa estimado del plan activo.

        Returns:
            ConsumptionRate con avg_weekly_consumption, data_points y confidence.
        """
        ingredient = await self._ingredient_repo.get_ingredient(ingredient_id)
        if ingredient is None:
            return ConsumptionRate(
                ingredient_id=ingredient_id,
                avg_weekly_consumption=0.0,
                data_points=0,
                confidence=0.0,
                source="estimated",
            )

        # Nombres a buscar: nombre principal + aliases
        search_names = {ingredient.name.lower()}
        search_names.update(a.lower() for a in (ingredient.aliases or []))

        plan_history = await self._planning_repo.get_plan_history(user_id, limit=_HISTORY_WEEKS)
        weekly_quantities: list[float] = []

        for plan in plan_history:
            items = plan.shopping_list_json.get("items", [])
            for item in items:
                item_name = item.get("ingredient_name", "").lower()
                if item_name in search_names:
                    qty = item.get("quantity", 0.0)
                    if qty > 0:
                        weekly_quantities.append(float(qty))
                    break

        data_points = len(weekly_quantities)

        if data_points >= _MIN_DATA_POINTS:
            avg = sum(weekly_quantities) / data_points
            confidence = min(data_points / _FULL_CONFIDENCE_WEEKS, 1.0)
            source = "historical"
        else:
            # Fallback: estimar desde el plan activo
            avg = await self._estimate_from_active_plan(user_id, search_names)
            confidence = 0.3 if avg > 0 else 0.0
            data_points = 1 if avg > 0 else 0
            source = "estimated"
            logger.info(
                "ConsumptionRate: ingredient_id=%d tiene solo %d semana(s) de historial, "
                "usando estimado (%.2f/semana).",
                ingredient_id, len(weekly_quantities), avg,
            )

        return ConsumptionRate(
            ingredient_id=ingredient_id,
            avg_weekly_consumption=avg,
            data_points=data_points,
            confidence=confidence,
            source=source,
        )

    async def validate_purchase_suggestion(
        self,
        user_id: int,
        ingredient_id: int,
        suggested_quantity: float,
        shelf_life_days: int,
    ) -> PurchaseValidation:
        """Valida si la cantidad sugerida se va a consumir antes del vencimiento.

        Lógica:
        1. Calcula consumption_rate.
        2. Calcula días para consumir la cantidad sugerida.
        3. Si días_para_consumir > shelf_life_days → WARNING + cantidad ajustada.
        4. Si no → OK.

        Returns:
            PurchaseValidation con is_valid, cantidad ajustada y porcentaje de desperdicio.
        """
        rate = await self.calculate_consumption_rate(user_id, ingredient_id)

        if rate.avg_weekly_consumption <= 0:
            # Sin datos de consumo: no podemos validar, asumir OK
            return PurchaseValidation(
                is_valid=True,
                original_quantity=suggested_quantity,
                suggested_quantity_adjusted=None,
                days_to_consume=0.0,
                shelf_life_days=shelf_life_days,
                waste_risk_percentage=0.0,
                message="Sin historial de consumo — cantidad no ajustada.",
            )

        daily_consumption = rate.avg_weekly_consumption / 7.0
        days_to_consume = suggested_quantity / daily_consumption

        if days_to_consume <= shelf_life_days:
            return PurchaseValidation(
                is_valid=True,
                original_quantity=suggested_quantity,
                suggested_quantity_adjusted=None,
                days_to_consume=round(days_to_consume, 1),
                shelf_life_days=shelf_life_days,
                waste_risk_percentage=0.0,
                message=(
                    f"Cantidad adecuada: vas a consumir {suggested_quantity:.1f} "
                    f"en {days_to_consume:.0f} días (vida útil: {shelf_life_days} días)."
                ),
            )

        # Cantidad excesiva → ajustar
        adjusted = rate.avg_weekly_consumption * (shelf_life_days / 7.0) * _SAFETY_FACTOR
        adjusted = max(adjusted, 0.0)
        waste_risk = ((suggested_quantity - adjusted) / suggested_quantity) * 100

        ingredient = await self._ingredient_repo.get_ingredient(ingredient_id)
        name = ingredient.name if ingredient else f"ingrediente #{ingredient_id}"

        return PurchaseValidation(
            is_valid=False,
            original_quantity=suggested_quantity,
            suggested_quantity_adjusted=round(adjusted, 2),
            days_to_consume=round(days_to_consume, 1),
            shelf_life_days=shelf_life_days,
            waste_risk_percentage=round(waste_risk, 1),
            message=(
                f"⚠️ Vas a comprar más {name} de lo que consumís antes del vencimiento "
                f"({days_to_consume:.0f} días para consumir vs {shelf_life_days} días de vida útil). "
                f"Cantidad ajustada: {adjusted:.1f} (ahorrás {waste_risk:.0f}% de desperdicio)."
            ),
        )

    async def get_waste_risk_report(self, user_id: int) -> list[WasteRiskItem]:
        """Reporte de riesgo de desperdicio para todo el pantry actual.

        Para cada item en el pantry:
        - Calcula días restantes de vida útil.
        - Calcula días para consumirlo al ritmo actual.
        - Clasifica el riesgo.

        Returns:
            Lista de WasteRiskItem ordenada por riesgo descendente.
        """
        from datetime import datetime

        pantry = await self._market_repo.get_pantry(user_id)
        report: list[WasteRiskItem] = []

        for item in pantry:
            if item.expires_at is None:
                # Sin fecha de vencimiento → riesgo bajo, asumir 30 días
                days_remaining = 30
            else:
                now = datetime.utcnow()
                expires = item.expires_at if item.expires_at.tzinfo is None else item.expires_at.replace(tzinfo=None)
                delta = expires - now
                days_remaining = max(0, delta.days)

            rate = await self.calculate_consumption_rate(user_id, item.ingredient_id)

            if rate.avg_weekly_consumption > 0:
                daily = rate.avg_weekly_consumption / 7.0
                days_to_consume = item.quantity_amount / daily
            else:
                days_to_consume = float("inf")

            # Clasificar acción
            if days_to_consume == float("inf"):
                waste_risk = 0.0
                action = "ok"
            elif days_to_consume > days_remaining * 1.0:
                waste_risk = min((days_to_consume - days_remaining) / days_to_consume, 1.0)
                action = "will_waste"
            elif days_to_consume > days_remaining * 0.8:
                waste_risk = 0.3
                action = "consume_soon"
            else:
                waste_risk = 0.0
                action = "ok"

            report.append(WasteRiskItem(
                pantry_item=item,
                days_remaining=days_remaining,
                days_to_consume=round(days_to_consume, 1) if days_to_consume != float("inf") else 999,
                waste_risk=round(waste_risk, 2),
                action=action,
            ))

        # Ordenar por riesgo descendente
        report.sort(key=lambda x: x.waste_risk, reverse=True)
        return report

    async def _estimate_from_active_plan(
        self, user_id: int, search_names: set[str]
    ) -> float:
        """Estima consumo semanal desde el plan activo (fallback con pocos datos históricos)."""
        active_plan = await self._planning_repo.get_active_plan(user_id)
        if active_plan is None:
            return 0.0

        items = active_plan.shopping_list_json.get("items", [])
        for item in items:
            if item.get("ingredient_name", "").lower() in search_names:
                return float(item.get("quantity", 0.0))
        return 0.0
