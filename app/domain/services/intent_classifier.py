"""Clasificador de intenciones por regex/keywords — sin IA.

El 80% de las intenciones de Félix son predecibles. Este clasificador
resuelve intenciones simples directamente sin pasar por el LLM.
Solo las intenciones ambiguas o complejas escalan al LLM.
"""

import re
from enum import Enum
from typing import Optional, Tuple


class Intent(Enum):
    QUERY_PLAN = "query_plan"
    QUERY_PANTRY = "query_pantry"
    QUERY_PRICE = "query_price"
    QUERY_HEALTH = "query_health"
    QUERY_REPORT = "query_report"
    QUERY_CORRELATIONS = "query_correlations"
    QUERY_TDEE = "query_tdee"
    REGISTER_PRICE = "register_price"
    REGISTER_HEALTH = "register_health"
    REGISTER_RECEIPT = "register_receipt"
    LOG_MEAL = "log_meal"
    GENERAL_CHAT = "general_chat"
    UNKNOWN = "unknown"


class IntentClassifier:
    """Clasificador de intenciones por regex. No usa IA."""

    PATTERNS: dict[Intent, list[str]] = {
        Intent.QUERY_PLAN: [
            r"qu[eé]\s+(?:cen[oa]|almuerz[oa]|com[oa]|desayun[oa])",
            r"plan\s+(?:de\s+)?(?:comida|semanal|hoy)",
            r"(?:men[uú]|menú)\s+(?:de\s+)?hoy",
            r"qu[eé]\s+(?:hay|toca)\s+(?:para|de)\s+(?:comer|cenar|almorzar)",
            r"qu[eé]\s+como\s+hoy",
        ],
        Intent.QUERY_PANTRY: [
            r"(?:alacena|despensa|pantry)",
            r"qu[eé]\s+tengo\s+(?:en\s+)?(?:casa|la\s+alacena)",
            r"(?:stock|inventario)\s+(?:de\s+)?(?:comida|alimentos)",
        ],
        Intent.QUERY_PRICE: [
            r"(?:cu[aá]nto|cuanto)\s+(?:cuesta|sale|vale)",
            r"precio\s+(?:de|del)",
            r"(?:m[aá]s\s+)?barato",
            r"historial\s+(?:de\s+)?precio",
        ],
        Intent.QUERY_HEALTH: [
            r"(?:c[oó]mo|como)\s+(?:dorm[ií]|descans[eé])",
            r"(?:sue[ñn]o|hrv|estr[eé]s|estres|pasos|salud)",
            r"(?:datos|registro)\s+(?:de\s+)?salud",
            r"(?:c[oó]mo|como)\s+estoy\s+(?:de\s+)?(?:salud|energía)",
        ],
        Intent.QUERY_REPORT: [
            r"reporte\s+(?:semanal|mensual)",
            r"(?:res[uú]men|resumen)\s+(?:de\s+la\s+)?semana",
        ],
        Intent.QUERY_CORRELATIONS: [
            r"correlaci[oó]n",
            r"relaci[oó]n\s+entre\s+(?:sue[ñn]o|estr[eé]s|comida)",
            r"mood\s*(?:&|and|y)\s*food",
        ],
        Intent.QUERY_TDEE: [
            r"(?:cu[aá]ntas|cuantas)\s+calor[ií]as\s+(?:necesito|puedo|tengo)",
            r"tdee",
            r"gasto\s+cal[oó]rico",
        ],
        Intent.REGISTER_PRICE: [
            r"compr[eé]\s+.+\$",
            r"\$\s*\d+.+(?:kilo|kg|unidad|litro|lt)",
            r"(?:registr[aá]|anotá)\s+(?:precio|que\s+compr[eé])",
        ],
        Intent.REGISTER_HEALTH: [
            r"(?:mi\s+)?estr[eé]s\s+(?:es|hoy|está)\s+\d",
            r"(?:registr[aá]|anotá)\s+(?:estrés|sueño|mood|estres)",
            r"(?:hoy\s+)?(?:me\s+siento|estoy)\s+(?:bien|mal|regular|cansado|estresado)",
            r"dorm[ií]\s+\d",
        ],
        Intent.LOG_MEAL: [
            r"(?:almorcé|comí|cené|desayuné)\s+",
            r"(?:registr[aá]|anotá)\s+(?:que\s+)?(?:comí|almorcé|cené)",
            r"me\s+com[ií]\s+",
        ],
    }

    @classmethod
    def classify(cls, text: str) -> Tuple[Intent, float]:
        """Retorna (intent, confidence). Confidence 1.0 = regex match, 0.0 = unknown."""
        text_lower = text.lower().strip()
        for intent, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return (intent, 1.0)
        return (Intent.UNKNOWN, 0.0)

    @classmethod
    def get_endpoint(cls, intent: Intent) -> Optional[str]:
        """Mapea intent a endpoint SGAI."""
        MAPPING: dict[Intent, str] = {
            Intent.QUERY_PLAN: "GET /api/v1/plans/current",
            Intent.QUERY_PANTRY: "GET /api/v1/market/pantry/1/named",
            Intent.QUERY_HEALTH: "GET /api/v1/health/latest/1",
            Intent.QUERY_REPORT: "GET /api/v1/mood-food/report/1",
            Intent.QUERY_CORRELATIONS: "GET /api/v1/mood-food/correlations/1",
            Intent.QUERY_TDEE: "GET /api/v1/health/tdee/1",
        }
        return MAPPING.get(intent)

    @classmethod
    def requires_llm(cls, intent: Intent) -> bool:
        """Retorna True si la intención requiere procesamiento por LLM."""
        return intent in (Intent.UNKNOWN, Intent.REGISTER_PRICE,
                          Intent.REGISTER_HEALTH, Intent.REGISTER_RECEIPT,
                          Intent.LOG_MEAL, Intent.GENERAL_CHAT)
