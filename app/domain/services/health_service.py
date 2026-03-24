"""
Servicio de cálculo de TDEE dinámico con ajustes por biomarcadores.

Fórmula Harris-Benedict revisada (Mifflin-St Jeor adaptada) con:
- Factor de actividad (5 niveles)
- Factor de objetivo nutricional
- Ajuste dinámico por estrés alto (-5%)
- Ajuste dinámico por sueño pobre (-5%)
- Acumulación máxima: -10%
"""

from dataclasses import dataclass

from app.domain.models.health import HealthLog
from app.domain.models.user import UserProfile

# Multiplicadores por nivel de actividad
_ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# Ajuste por objetivo nutricional
_GOAL_MULTIPLIERS: dict[str, float] = {
    "maintain": 1.0,
    "lose": 0.85,
    "gain": 1.15,
}

# Umbrales para ajustes dinámicos (ADR-008)
_STRESS_HIGH_THRESHOLD = 7.0   # Por encima: estrés elevado
_SLEEP_POOR_THRESHOLD = 60.0   # Por debajo: sueño pobre
_DYNAMIC_ADJUSTMENT = -0.05    # -5% por cada factor de fatiga
_MAX_ADJUSTMENT = -0.10        # Máximo -10% acumulado


@dataclass
class TDEEResult:
    """Resultado del cálculo TDEE con desglose completo."""
    bmr: float                   # BMR base (Harris-Benedict)
    activity_multiplier: float   # Multiplicador de actividad
    goal_multiplier: float       # Multiplicador de objetivo
    stress_adjustment: float     # Ajuste por estrés (0 o -0.05)
    sleep_adjustment: float      # Ajuste por sueño (0 o -0.05)
    tdee: int                    # TDEE final en kcal/día
    breakdown: dict              # Desglose legible para display


class HealthService:
    """Servicio de cálculo de métricas de salud y TDEE dinámico."""

    def calculate_tdee(
        self,
        profile: UserProfile,
        metrics: HealthLog | None = None,
    ) -> TDEEResult:
        """
        Calcula el TDEE con ajustes dinámicos por biomarcadores.

        1. BMR base (Harris-Benedict revisado — masculino):
           88.362 + (13.397 × peso_kg) + (4.799 × altura_cm) - (5.677 × edad)

        2. Factor de actividad:
           sedentary=1.2, light=1.375, moderate=1.55, active=1.725, very_active=1.9

        3. Ajuste por objetivo:
           maintain=1.0, lose=0.85, gain=1.15

        4. Ajuste dinámico por estrés/sueño:
           - Si stress_level > 7: -5%
           - Si sleep_score < 60: -5%
           - Máximo acumulado: -10%

        Args:
            profile: Perfil del usuario con datos antropométricos.
            metrics: Último log de salud (opcional — si None, sin ajustes dinámicos).

        Returns:
            TDEEResult con el TDEE final y desglose completo.
        """
        # 1. BMR base (Harris-Benedict revisado)
        bmr = (
            88.362
            + (13.397 * profile.weight_kg)
            + (4.799 * profile.height_cm)
            - (5.677 * profile.age)
        )

        # 2. Factor de actividad
        activity_multiplier = _ACTIVITY_MULTIPLIERS.get(profile.activity_level, 1.55)

        # 3. Factor de objetivo
        goal_multiplier = _GOAL_MULTIPLIERS.get(profile.goal, 1.0)

        # 4. Ajustes dinámicos por biomarcadores
        stress_adjustment = 0.0
        sleep_adjustment = 0.0

        if metrics is not None:
            if metrics.stress_level is not None and metrics.stress_level > _STRESS_HIGH_THRESHOLD:
                stress_adjustment = _DYNAMIC_ADJUSTMENT

            if metrics.sleep_score is not None and metrics.sleep_score < _SLEEP_POOR_THRESHOLD:
                sleep_adjustment = _DYNAMIC_ADJUSTMENT

        # Acumulación con techo de -10%
        total_adjustment = max(stress_adjustment + sleep_adjustment, _MAX_ADJUSTMENT)

        # 5. TDEE final
        tdee_raw = bmr * activity_multiplier * goal_multiplier * (1 + total_adjustment)
        tdee = int(round(tdee_raw))

        # Desglose legible
        breakdown = {
            "bmr_kcal": round(bmr, 1),
            "after_activity": round(bmr * activity_multiplier, 1),
            "after_goal": round(bmr * activity_multiplier * goal_multiplier, 1),
            "stress_adjustment_pct": int(stress_adjustment * 100),
            "sleep_adjustment_pct": int(sleep_adjustment * 100),
            "total_adjustment_pct": int(total_adjustment * 100),
            "final_tdee_kcal": tdee,
            "activity_level": profile.activity_level,
            "goal": profile.goal,
        }

        return TDEEResult(
            bmr=round(bmr, 1),
            activity_multiplier=activity_multiplier,
            goal_multiplier=goal_multiplier,
            stress_adjustment=stress_adjustment,
            sleep_adjustment=sleep_adjustment,
            tdee=tdee,
            breakdown=breakdown,
        )
