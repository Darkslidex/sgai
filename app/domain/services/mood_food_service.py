"""
Servicio de correlación entre alimentación y bienestar.
Analiza datos históricos para encontrar patrones Mood & Food.

Requiere mínimo 4 semanas de datos de salud para generar insights.
"""

import json
import logging
import math
from datetime import date, datetime, timedelta

from app.domain.ports.health_repository import HealthRepositoryPort
from app.domain.ports.planning_repository import PlanningRepositoryPort

logger = logging.getLogger(__name__)

_MIN_WEEKS = 4
_HISTORY_WEEKS = 8
_INSIGHTS_CACHE_SECONDS = 7 * 86400  # 7 días


class MoodFoodService:
    def __init__(
        self,
        health_repo: HealthRepositoryPort,
        planning_repo: PlanningRepositoryPort,
        llm=None,  # DeepSeekAdapter — duck typing para evitar dependencia circular
    ) -> None:
        self._health_repo = health_repo
        self._planning_repo = planning_repo
        self._llm = llm
        self._insights_cache: dict[int, tuple[datetime, list[dict]]] = {}

    # ── Datos disponibles ────────────────────────────────────────────────────

    async def has_enough_data(self, user_id: int) -> tuple[bool, int]:
        """
        Verificar si hay suficientes datos para análisis.
        Retorna (tiene_suficiente, semanas_disponibles).
        Mínimo: 4 semanas con al menos un health log.
        """
        end = date.today()
        start = end - timedelta(weeks=_HISTORY_WEEKS)
        logs = await self._health_repo.get_logs(user_id, start, end)

        weeks_with_data: set[date] = set()
        for log in logs:
            week_start = log.date - timedelta(days=log.date.weekday())
            weeks_with_data.add(week_start)

        available_weeks = len(weeks_with_data)
        return available_weeks >= _MIN_WEEKS, available_weeks

    # ── Correlaciones ────────────────────────────────────────────────────────

    async def calculate_correlations(self, user_id: int) -> dict:
        """
        Calcular correlaciones de Pearson entre variables de salud y plan.

        Variables: sleep_score, stress_level, hrv, steps, plan_cost.
        Retorna dict con todas las correlaciones + las más fuertes.
        """
        end = date.today()
        start = end - timedelta(weeks=_HISTORY_WEEKS)
        logs = await self._health_repo.get_logs(user_id, start, end)
        plans = await self._planning_repo.get_plan_history(user_id, limit=_HISTORY_WEEKS)

        # Agrupar logs por semana
        weekly_health: dict[date, list] = {}
        for log in logs:
            week_start = log.date - timedelta(days=log.date.weekday())
            weekly_health.setdefault(week_start, []).append(log)

        # Construir promedios semanales
        weeks_data: list[dict] = []
        for week_start, week_logs in sorted(weekly_health.items()):
            sleep_vals = [l.sleep_score for l in week_logs if l.sleep_score is not None]
            stress_vals = [l.stress_level for l in week_logs if l.stress_level is not None]
            hrv_vals = [l.hrv for l in week_logs if l.hrv is not None]
            steps_vals = [l.steps for l in week_logs if l.steps is not None]

            weeks_data.append({
                "week": week_start,
                "sleep_score": sum(sleep_vals) / len(sleep_vals) if sleep_vals else None,
                "stress_level": sum(stress_vals) / len(stress_vals) if stress_vals else None,
                "hrv": sum(hrv_vals) / len(hrv_vals) if hrv_vals else None,
                "steps": sum(steps_vals) / len(steps_vals) if steps_vals else None,
                "plan_cost": None,
            })

        # Asociar costo del plan por semana
        plan_costs: dict[date, float] = {}
        for plan in plans:
            week_start = plan.week_start - timedelta(days=plan.week_start.weekday())
            plan_costs[week_start] = plan.total_cost_ars
        for w in weeks_data:
            w["plan_cost"] = plan_costs.get(w["week"])

        # Calcular correlaciones Pearson para los pares de variables
        pairs = [
            ("sleep_score", "stress_level"),
            ("sleep_score", "hrv"),
            ("stress_level", "hrv"),
            ("sleep_score", "plan_cost"),
            ("stress_level", "plan_cost"),
            ("steps", "sleep_score"),
        ]

        correlations: dict[str, float | None] = {}
        for x_key, y_key in pairs:
            x_vals = [w[x_key] for w in weeks_data
                      if w.get(x_key) is not None and w.get(y_key) is not None]
            y_vals = [w[y_key] for w in weeks_data
                      if w.get(x_key) is not None and w.get(y_key) is not None]
            r = _pearson(x_vals, y_vals)
            correlations[f"{x_key}_vs_{y_key}"] = round(r, 3) if r is not None else None

        valid = {k: v for k, v in correlations.items() if v is not None}
        strongest_pos = max(valid.items(), key=lambda x: x[1], default=(None, 0))
        strongest_neg = min(valid.items(), key=lambda x: x[1], default=(None, 0))

        return {
            "correlations": correlations,
            "strongest_positive": {
                "pair": strongest_pos[0].replace("_vs_", " ↔ ") if strongest_pos[0] else None,
                "r": strongest_pos[1],
            },
            "strongest_negative": {
                "pair": strongest_neg[0].replace("_vs_", " ↔ ") if strongest_neg[0] else None,
                "r": strongest_neg[1],
            },
            "weeks_analyzed": len(weeks_data),
            "calculated_at": datetime.utcnow().isoformat(),
        }

    # ── Insights ─────────────────────────────────────────────────────────────

    async def generate_insights(self, user_id: int) -> list[dict]:
        """
        Generar 3-5 insights accionables usando el LLM.
        Cachea resultados por 7 días.
        """
        # Verificar caché
        cached = self._insights_cache.get(user_id)
        if cached:
            cache_time, insights = cached
            age_seconds = (datetime.utcnow() - cache_time).total_seconds()
            if age_seconds < _INSIGHTS_CACHE_SECONDS:
                return insights

        has_data, weeks = await self.has_enough_data(user_id)
        if not has_data:
            return []

        corr_data = await self.calculate_correlations(user_id)

        if self._llm is None:
            return []

        user_content = (
            f"Datos de correlación del usuario (últimas {corr_data['weeks_analyzed']} semanas):\n"
            f"{json.dumps(corr_data['correlations'], ensure_ascii=False, indent=2)}\n\n"
            f"Correlación más positiva: {corr_data['strongest_positive']}\n"
            f"Correlación más negativa: {corr_data['strongest_negative']}\n\n"
            "Generá entre 3 y 5 insights accionables."
        )

        try:
            from app.adapters.llm.prompts.mood_food_prompt import MOOD_FOOD_SYSTEM
            response_text = await self._llm.generate_text(MOOD_FOOD_SYSTEM, user_content)
            data = json.loads(response_text)
            insights = data.get("insights", [])
            if not isinstance(insights, list):
                insights = []
            insights = insights[:5]
        except Exception as e:
            logger.error("Error generating Mood & Food insights: %s", e)
            insights = []

        self._insights_cache[user_id] = (datetime.utcnow(), insights)
        return insights

    # ── Reporte semanal ──────────────────────────────────────────────────────

    async def get_weekly_report(self, user_id: int) -> dict:
        """
        Reporte semanal consolidado de salud + plan + insight principal.
        """
        end = date.today()
        week_start = end - timedelta(days=end.weekday())
        week_end = week_start + timedelta(days=6)

        logs = await self._health_repo.get_logs(user_id, week_start, week_end)
        plans = await self._planning_repo.get_plan_history(user_id, limit=1)

        sleep_vals = [l.sleep_score for l in logs if l.sleep_score is not None]
        stress_vals = [l.stress_level for l in logs if l.stress_level is not None]
        steps_vals = [l.steps for l in logs if l.steps is not None]

        avg_sleep = round(sum(sleep_vals) / len(sleep_vals), 1) if sleep_vals else None
        avg_stress_num = sum(stress_vals) / len(stress_vals) if stress_vals else None
        avg_stress_label = (
            "bajo" if avg_stress_num is not None and avg_stress_num < 4 else
            "medio" if avg_stress_num is not None and avg_stress_num < 7 else
            "alto" if avg_stress_num is not None else None
        )
        avg_steps = int(sum(steps_vals) / len(steps_vals)) if steps_vals else None

        active_plan = plans[0] if plans else None
        plan_cost = active_plan.total_cost_ars if active_plan else None

        mood_insight = None
        recommendation = None
        has_data, _ = await self.has_enough_data(user_id)
        if has_data:
            insights = await self.generate_insights(user_id)
            if insights:
                mood_insight = insights[0].get("insight")
                recommendation = insights[0].get("recommendation")

        return {
            "week": f"{week_start.strftime('%d/%m')}–{week_end.strftime('%d/%m %Y')}",
            "health_summary": {
                "avg_sleep": avg_sleep,
                "avg_stress": avg_stress_label,
                "avg_steps": avg_steps,
            },
            "plan_summary": {
                "cost_ars": plan_cost,
            },
            "mood_food_insight": mood_insight,
            "recommendation_for_next_week": recommendation,
        }


# ── Estadística ──────────────────────────────────────────────────────────────

def _pearson(x: list[float], y: list[float]) -> float | None:
    """Coeficiente de correlación de Pearson entre dos listas de igual longitud."""
    n = len(x)
    if n < 2:
        return None

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

    if den_x == 0 or den_y == 0:
        return None

    return numerator / (den_x * den_y)
