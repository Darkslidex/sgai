"""
Chef Ejecutivo — Planning Service.

Orquesta la generación del plan semanal Batch Cooking 1x5:
1. Verifica caché (plan activo no expirado)
2. Construye PlanningContext con toda la info del usuario
3. Llama al AIPlannerPort (DeepSeek)
4. Valida la respuesta contra la DB (ingredientes + storage ADR-008)
5. Descuenta pantry de la lista de compras
6. Persiste el plan
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.domain.models.planning import WeeklyPlan
from app.domain.validators.plan_validator import ValidatedWeeklyPlan, validate_weekly_plan
from app.domain.models.recipe import Recipe
from app.domain.ports.ai_planner_port import (
    AIPlannerPort,
    PlanningContext,
    ShoppingItem,
    WeeklyPlanResult,
)
from app.domain.ports.health_data_port import HealthDataPort
from app.domain.ports.ingredient_repository import IngredientRepositoryPort
from app.domain.ports.market_repository import MarketRepositoryPort
from app.domain.ports.planning_repository import PlanningRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort
from app.domain.services.energy_mode_service import EnergyModeService, EnergyState
from app.domain.services.health_service import HealthService, TDEEResult

# Import opcional para evitar dependencia circular en fases anteriores
try:
    from app.domain.services.consumption_ratio_service import ConsumptionRatioService
except ImportError:
    ConsumptionRatioService = None  # type: ignore[assignment,misc]


@dataclass
class DailySuggestion:
    """Sugerencia diaria del sistema con contexto energético."""
    recipes: list[Recipe]
    energy_state: EnergyState
    tdee: TDEEResult

logger = logging.getLogger(__name__)

_ACTIVITY_TDEE = {
    "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
    "active": 1.725, "very_active": 1.9,
}
_CACHE_DAYS = 7


def _estimate_tdee(weight_kg: float, height_cm: float, age: int, activity_level: str) -> int:
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return int(bmr * _ACTIVITY_TDEE.get(activity_level, 1.55))


def _validate_storage(result: WeeklyPlanResult, max_storage: dict) -> None:
    """ADR-008: Verifica que el plan no exceda la capacidad física de almacenamiento.

    Advertencia (no bloquea): loguea un warning si el volumen estimado es excesivo.
    La conversión exacta kg→litros depende del producto; se usa 1:1 como aproximación.
    """
    if not max_storage:
        return

    # Agrupar por unidad de medida como proxy de volumen
    totals: dict[str, float] = {}
    for item in result.shopping_list:
        key = "líquidos" if item.unit in ("litro", "l", "ml") else "sólidos"
        totals[key] = totals.get(key, 0) + item.quantity

    max_total = sum(max_storage.values())
    estimated_total = sum(totals.values())

    if estimated_total > max_total * 1.5:
        logger.warning(
            "ADR-008: Plan podría exceder capacidad de almacenamiento. "
            "Estimado: %.1f unidades, Capacidad total: %.1f L",
            estimated_total, max_total,
        )


def _discount_pantry(result: WeeklyPlanResult, pantry_ingredient_ids: set[int]) -> WeeklyPlanResult:
    """Descuenta de la lista de compras lo que el usuario ya tiene en pantry.

    En Fase 2A, el LLM ya recibe el inventario en el contexto, así que este paso
    es una salvaguarda adicional (no modifica si el LLM ya lo consideró).
    """
    # El LLM ya consideró la pantry via el Context Prompt, así que no modificamos aquí.
    # Fase 3B implementará el descuento exacto por cantidad.
    return result


class PlanningService:
    """Orquestador del plan semanal — Chef Ejecutivo."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        market_repo: MarketRepositoryPort,
        planning_repo: PlanningRepositoryPort,
        ai_planner: AIPlannerPort,
        ingredient_repo: IngredientRepositoryPort,
        health_adapter: HealthDataPort | None = None,
        energy_mode_service: EnergyModeService | None = None,
        health_service: HealthService | None = None,
        consumption_ratio_service: "ConsumptionRatioService | None" = None,
    ) -> None:
        self._user_repo = user_repo
        self._market_repo = market_repo
        self._planning_repo = planning_repo
        self._ai_planner = ai_planner
        self._ingredient_repo = ingredient_repo
        self._health_adapter = health_adapter
        self._energy_mode_service = energy_mode_service or EnergyModeService()
        self._health_service = health_service or HealthService()
        self._consumption_ratio_service = consumption_ratio_service

    async def get_or_generate_plan(self, user_id: int, force: bool = False) -> WeeklyPlan:
        """Retorna el plan activo (si existe y no expiró) o genera uno nuevo."""
        now = datetime.now(timezone.utc)

        # ── 1. Verificar caché ───────────────────────────────────────────────
        if not force:
            active = await self._planning_repo.get_active_plan(user_id)
            if active is not None:
                # expires_at puede ser naive (sin tz); comparar ambos naive
                expires = active.expires_at
                if expires.tzinfo is None:
                    now_cmp = now.replace(tzinfo=None)
                else:
                    now_cmp = now
                if expires > now_cmp:
                    logger.info("Cache hit: plan activo para user_id=%d hasta %s", user_id, expires)
                    return active

        # ── 2. Construir contexto ────────────────────────────────────────────
        profile = await self._user_repo.get_profile(user_id)
        if profile is None:
            raise ValueError(f"Usuario {user_id} no encontrado")

        preferences = await self._user_repo.get_preferences(user_id)
        pantry = await self._market_repo.get_pantry(user_id)
        all_prices = await self._market_repo.get_all_current_prices()
        all_ingredients = await self._ingredient_repo.list_ingredients()
        plan_history = await self._planning_repo.get_plan_history(user_id, limit=3)
        tdee = _estimate_tdee(profile.weight_kg, profile.height_cm, profile.age, profile.activity_level)

        # Cruzar ingredientes con precios
        price_map = {p.ingredient_id: p for p in all_prices}
        priced = [
            (ing, price_map[ing.id])
            for ing in all_ingredients
            if ing.id in price_map
        ]

        context = PlanningContext(
            profile=profile,
            preferences=preferences,
            pantry=pantry,
            priced_ingredients=priced,
            plan_history=plan_history,
            tdee_kcal=tdee,
        )

        # ── 3. Generar plan con IA ───────────────────────────────────────────
        logger.info("Generando plan semanal con IA para user_id=%d (force=%s)", user_id, force)
        result = await self._ai_planner.generate_plan(context)
        logger.info(
            "Plan generado: %d días, costo ARS %.0f, tokens: %d",
            len(result.days), result.total_cost_ars, result.tokens_used,
        )

        # ── 4. Validaciones ──────────────────────────────────────────────────
        _validate_storage(result, profile.max_storage_volume)
        pantry_ids = {item.ingredient_id for item in pantry}
        result = _discount_pantry(result, pantry_ids)

        # ADR-008: Validar lista de compras contra Ratio Consumo/Vencimiento
        if self._consumption_ratio_service is not None:
            result = await self._validate_shopping_list(user_id, result)

        # ── 5. Validar output del LLM con Pydantic (anti-alucinaciones) ─────
        _plan_raw = {
            "days": [{"day": d.day, "lunch": d.lunch, "dinner": d.dinner} for d in result.days],
            "shopping_list": [
                {"name": i.ingredient_name, "quantity": i.quantity,
                 "unit": i.unit, "estimated_cost_ars": i.estimated_price_ars}
                for i in result.shopping_list
            ],
            "total_cost_ars": result.total_cost_ars,
            "cooking_day": result.cooking_day,
            "prep_steps": result.prep_steps,
        }
        try:
            validate_weekly_plan(_plan_raw)
        except Exception as val_exc:
            logger.error("Plan LLM falló validación Pydantic: %s | raw=%s", val_exc, _plan_raw)
            raise ValueError(
                f"El plan generado por IA contiene datos inválidos: {val_exc}"
            ) from val_exc

        # ── 6. Persistir ─────────────────────────────────────────────────────
        plan_json = {
            "days": [{"day": d.day, "lunch": d.lunch, "dinner": d.dinner} for d in result.days],
            "cooking_day": result.cooking_day,
            "prep_steps": result.prep_steps,
            "tokens_used": result.tokens_used,
        }
        shopping_json = {
            "items": [
                {
                    "ingredient_name": item.ingredient_name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "estimated_price_ars": item.estimated_price_ars,
                }
                for item in result.shopping_list
            ]
        }

        week_start = date.today()
        expires_at = datetime.now().replace(tzinfo=None) + timedelta(days=_CACHE_DAYS)

        plan = WeeklyPlan(
            id=0,
            user_id=user_id,
            week_start=week_start,
            plan_json=plan_json,
            shopping_list_json=shopping_json,
            total_cost_ars=result.total_cost_ars,
            is_active=True,
            created_at=datetime.now().replace(tzinfo=None),
            expires_at=expires_at,
        )
        return await self._planning_repo.save_plan(plan)

    async def _validate_shopping_list(
        self, user_id: int, result: WeeklyPlanResult
    ) -> WeeklyPlanResult:
        """ADR-008: Valida cada item de la lista de compras contra el Ratio Consumo/Vencimiento."""
        if self._consumption_ratio_service is None:
            return result

        validated_items: list[ShoppingItem] = []
        for item in result.shopping_list:
            # Buscar el ingrediente por nombre para obtener su ID y shelf_life
            matches = await self._ingredient_repo.search_ingredients(item.ingredient_name)
            if not matches:
                validated_items.append(item)
                continue

            ingredient = matches[0]
            shelf_life = ingredient.avg_shelf_life_days or 7

            validation = await self._consumption_ratio_service.validate_purchase_suggestion(
                user_id=user_id,
                ingredient_id=ingredient.id,
                suggested_quantity=item.quantity,
                shelf_life_days=shelf_life,
            )

            if not validation.is_valid and validation.suggested_quantity_adjusted is not None:
                logger.info(
                    "ADR-008: Ajustando cantidad de '%s': %.2f → %.2f (%s)",
                    item.ingredient_name,
                    item.quantity,
                    validation.suggested_quantity_adjusted,
                    validation.message,
                )
                validated_items.append(ShoppingItem(
                    ingredient_name=item.ingredient_name,
                    quantity=validation.suggested_quantity_adjusted,
                    unit=item.unit,
                    estimated_price_ars=item.estimated_price_ars
                    * (validation.suggested_quantity_adjusted / item.quantity),
                ))
            else:
                validated_items.append(item)

        # Recalcular costo total con las cantidades ajustadas
        total_cost = sum(i.estimated_price_ars for i in validated_items)
        return WeeklyPlanResult(
            days=result.days,
            shopping_list=validated_items,
            total_cost_ars=total_cost,
            cooking_day=result.cooking_day,
            prep_steps=result.prep_steps,
            tokens_used=result.tokens_used,
        )

    async def get_todays_suggestion(
        self,
        user_id: int,
        available_recipes: list[Recipe],
    ) -> DailySuggestion:
        """
        Genera la sugerencia diaria adaptada al estado energético del usuario.

        ADR-008: Si el usuario está en Modo Baja Energía, filtra recetas cortas
        o solo sugiere recalentar batch ya preparado.

        Args:
            user_id: ID del usuario.
            available_recipes: Lista de recetas disponibles para sugerir.

        Returns:
            DailySuggestion con recetas filtradas, estado energético y TDEE.
        """
        profile = await self._user_repo.get_profile(user_id)
        if profile is None:
            raise ValueError(f"Usuario {user_id} no encontrado")

        # Obtener métricas (None si no hay health_adapter o no hay datos)
        metrics = None
        if self._health_adapter is not None:
            metrics = await self._health_adapter.get_latest_metrics(user_id)

        energy_state = await self._energy_mode_service.evaluate_energy_state(user_id, metrics)
        tdee = self._health_service.calculate_tdee(profile, metrics)

        if energy_state in (EnergyState.LOW, EnergyState.CRITICAL):
            # ADR-008: Modo Baja Energía — filtrar recetas simples
            recipes = self._energy_mode_service.filter_recipes_for_low_energy(available_recipes)
            logger.info(
                "Modo Baja Energía (%s) activado para user_id=%d: %d recetas simples disponibles",
                energy_state, user_id, len(recipes),
            )
        else:
            recipes = available_recipes

        return DailySuggestion(
            recipes=recipes,
            energy_state=energy_state,
            tdee=tdee,
        )
