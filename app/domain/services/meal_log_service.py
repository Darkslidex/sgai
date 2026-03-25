"""Servicio de dominio para registro y consulta de consumo alimentario."""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.ingredient_repo import IngredientRepository
from app.adapters.persistence.meal_log_repo import MealLogRepository
from app.adapters.persistence.user_repo import UserRepository
from app.domain.models.meal_log import MealItem, MealLog
from app.domain.services.health_service import HealthService

logger = logging.getLogger(__name__)

_VALID_MEAL_TYPES = {"desayuno", "almuerzo", "cena", "snack"}


class MealLogService:
    """Orquesta el registro de comidas: LLM parsing + persistencia + resumen diario."""

    def __init__(self, session: AsyncSession, llm_port) -> None:
        self._session = session
        self._llm = llm_port
        self._meal_repo = MealLogRepository(session)
        self._ingredient_repo = IngredientRepository(session)
        self._user_repo = UserRepository(session)

    async def log_meal(
        self,
        user_id: int,
        target_date: date,
        description: str,
        meal_type: str | None = None,
        source: str = "text",
    ) -> MealLog:
        """Parsea una descripción de comida con el LLM, la persiste y retorna el MealLog.

        Args:
            user_id: ID del usuario en user_profiles.
            target_date: Fecha de la comida.
            description: Texto libre del usuario.
            meal_type: Tipo de comida; si es None, el LLM lo infiere.
            source: Origen del registro ('text', 'photo', 'voice').

        Returns:
            MealLog guardado en la DB con id asignado.

        Raises:
            ValueError: Si el LLM retorna datos inválidos.
        """
        # Obtener catálogo de ingredientes para que el LLM use nombres exactos
        ingredients = await self._ingredient_repo.list_ingredients()
        catalog = [ing.name for ing in ingredients]

        # Llamar al LLM para parsear la descripción
        parsed = await self._llm.parse_meal_description(
            description=description,
            ingredient_catalog=catalog,
        )

        items_data = parsed.get("items", [])
        if not items_data:
            raise ValueError(
                f"El LLM no pudo identificar ítems en la descripción: '{description}'"
            )

        # Determinar meal_type: el provisto por el usuario tiene prioridad
        resolved_meal_type = meal_type
        if resolved_meal_type is None:
            resolved_meal_type = parsed.get("meal_type_guess", "almuerzo")
        if resolved_meal_type not in _VALID_MEAL_TYPES:
            logger.warning(
                "meal_type inválido '%s' — usando 'almuerzo' por defecto", resolved_meal_type
            )
            resolved_meal_type = "almuerzo"

        # Construir lista de MealItem
        meal_items = [
            MealItem(
                ingredient=item["ingredient"],
                quantity_g=float(item["quantity_g"]),
                calories_kcal=float(item["calories_kcal"]),
                protein_g=float(item["protein_g"]) if item.get("protein_g") is not None else None,
            )
            for item in items_data
        ]

        total_calories = round(sum(i.calories_kcal for i in meal_items), 1)
        protein_values = [i.protein_g for i in meal_items if i.protein_g is not None]
        total_protein = round(sum(protein_values), 1) if protein_values else None

        from datetime import datetime

        meal_log = MealLog(
            id=0,
            user_id=user_id,
            date=target_date,
            meal_type=resolved_meal_type,
            raw_description=description,
            items=meal_items,
            total_calories_kcal=total_calories,
            total_protein_g=total_protein,
            source=source,
            notes=None,
            created_at=datetime.utcnow(),
        )

        saved = await self._meal_repo.save(meal_log)
        logger.info(
            "MealLog guardado — user_id=%d date=%s meal_type=%s calories=%.1f",
            user_id, target_date, resolved_meal_type, total_calories,
        )
        return saved

    async def get_daily_summary(self, user_id: int, target_date: date) -> dict:
        """Retorna el resumen del día con calorías totales, proteínas y calorías restantes vs TDEE.

        Args:
            user_id: ID del usuario.
            target_date: Fecha a consultar.

        Returns:
            dict con total_calories_kcal, total_protein_g, meals, tdee_kcal, calories_remaining.
        """
        summary = await self._meal_repo.get_daily_summary(user_id, target_date)

        # Calcular TDEE desde el perfil del usuario
        tdee_kcal: int | None = None
        calories_remaining: float | None = None

        profile = await self._user_repo.get_profile(user_id)
        if profile is not None:
            health_service = HealthService()
            tdee_result = health_service.calculate_tdee(profile, metrics=None)
            tdee_kcal = tdee_result.tdee
            calories_remaining = round(tdee_kcal - summary["total_calories_kcal"], 1)

        return {
            **summary,
            "tdee_kcal": tdee_kcal,
            "calories_remaining": calories_remaining,
        }
