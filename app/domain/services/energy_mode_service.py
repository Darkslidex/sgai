"""
Modo Baja Energía — ADR-008.

Transición de arquitectura reactiva a predictiva.
Usa biomarcadores para simplificar automáticamente la interacción
y las recetas sugeridas cuando el usuario está agotado.

Fuente de datos: HRV (Heart Rate Variability) y Sleep Score
del Samsung Galaxy Watch 7 via Health Connect o input manual.
"""

import logging
from enum import Enum

from app.domain.models.health import HealthLog
from app.domain.models.recipe import Recipe

logger = logging.getLogger(__name__)


class EnergyState(str, Enum):
    NORMAL = "normal"
    LOW = "low"
    CRITICAL = "critical"


class EnergyModeService:
    """
    ADR-008: Modo Baja Energía.

    Evalúa biomarcadores para determinar el estado energético del usuario
    y adaptar la experiencia en consecuencia.
    """

    # Umbrales explícitos (ADR-008)
    HRV_LOW_THRESHOLD = 40      # ms — por debajo = estrés alto
    SLEEP_POOR_THRESHOLD = 55   # score 0-100 — por debajo = mal descanso
    STRESS_HIGH_THRESHOLD = 7   # escala 0-10 — por encima = estrés elevado

    # Configuración del modo
    MAX_RECIPE_TIME_MINUTES = 10  # Recetas ≤10 min en modo baja energía
    MAX_RECIPE_STEPS = 5          # Máximo 5 pasos de preparación

    async def evaluate_energy_state(
        self,
        user_id: int,
        metrics: HealthLog | None,
    ) -> EnergyState:
        """
        Evalúa el estado energético del usuario y determina si activar
        el Modo Baja Energía.

        Retorna:
        - EnergyState.NORMAL: Todo bien, flujo completo
        - EnergyState.LOW: Activar Modo Baja Energía
        - EnergyState.CRITICAL: Baja Energía + sugerir descanso

        Lógica:
        1. Si HRV < 40ms Y sleep_score < 55 → CRITICAL
        2. Si HRV < 40ms O sleep_score < 55 O stress > 7 → LOW
        3. Else → NORMAL

        Si no hay métricas disponibles: NORMAL (no penalizar por falta de datos).
        """
        if metrics is None:
            logger.debug("evaluate_energy_state: sin métricas para user_id=%d → NORMAL", user_id)
            return EnergyState.NORMAL

        hrv = metrics.hrv
        sleep = metrics.sleep_score
        stress = metrics.stress_level

        hrv_low = hrv is not None and hrv < self.HRV_LOW_THRESHOLD
        sleep_poor = sleep is not None and sleep < self.SLEEP_POOR_THRESHOLD
        stress_high = stress is not None and stress > self.STRESS_HIGH_THRESHOLD

        if hrv_low and sleep_poor:
            logger.info(
                "EnergyState CRITICAL para user_id=%d: HRV=%.1f ms, sleep=%.1f",
                user_id, hrv, sleep,
            )
            return EnergyState.CRITICAL

        if hrv_low or sleep_poor or stress_high:
            logger.info(
                "EnergyState LOW para user_id=%d: HRV=%s ms, sleep=%s, stress=%s",
                user_id, hrv, sleep, stress,
            )
            return EnergyState.LOW

        return EnergyState.NORMAL

    def filter_recipes_for_low_energy(self, recipes: list[Recipe]) -> list[Recipe]:
        """
        Filtra recetas compatibles con Modo Baja Energía:
        - prep_time_minutes <= 10
        - Priorizar tag "baja_energia" o "rapida"
        - Máximo 5 pasos de preparación (aproximado por prep_time)
        - Preferir recetas que ya están en batch (solo recalentar)

        Si ninguna receta pasa el filtro, retorna las ordenadas por menor tiempo.
        """
        preferred_tags = {"baja_energia", "rapida", "batch"}

        # Filtrar por tiempo
        fast_recipes = [
            r for r in recipes
            if r.prep_time_minutes <= self.MAX_RECIPE_TIME_MINUTES
        ]

        if not fast_recipes:
            # Fallback: las 3 más rápidas
            return sorted(recipes, key=lambda r: r.prep_time_minutes)[:3]

        # Ordenar: primero las que tienen tags preferidas, luego por tiempo
        def _priority(r: Recipe) -> tuple[int, int]:
            has_tag = int(any(t in preferred_tags for t in (r.tags or [])))
            return (-has_tag, r.prep_time_minutes)

        return sorted(fast_recipes, key=_priority)

    def simplify_bot_response(self, full_response: str, energy_state: EnergyState) -> str:
        """
        Si LOW/CRITICAL: condensar respuesta del bot.
        - Eliminar detalles nutricionales extensos
        - Ir directo a la acción
        - En CRITICAL: agregar mensaje de cuidado
        """
        if energy_state == EnergyState.NORMAL:
            return full_response

        # Tomar solo las primeras 2 líneas no vacías como resumen
        lines = [l for l in full_response.splitlines() if l.strip()]
        summary = "\n".join(lines[:2]) if lines else full_response

        if energy_state == EnergyState.CRITICAL:
            return (
                f"{summary}\n\n"
                "Hoy descansá, dejá que el batch cooking haga su trabajo. "
                "Solo recalentá lo que ya tenés preparado."
            )

        return f"{summary}\n_(Modo Baja Energía: respuesta simplificada)_"
