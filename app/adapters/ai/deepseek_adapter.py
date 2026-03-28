"""
Adapter de DeepSeek para el motor de planificación de SGAI.

Implementa AIPlannerPort usando la API de DeepSeek.
Temperatura 0.2 para respuestas deterministas.
Retry con backoff exponencial (3 intentos, timeout 60s).
"""

import asyncio
import json
import logging

import httpx
from pydantic import BaseModel, ValidationError

from app.adapters.llm.llm_router import LLMRouter, TaskType

from app.adapters.ai.prompts.planning_prompts import (
    SYSTEM_PROMPT,
    TASK_PROMPT,
    build_context_prompt,
)
from app.domain.ports.ai_planner_port import (
    AIPlannerPort,
    DayMeals,
    PlanningContext,
    ShoppingItem,
    SwapRequest,
    SwapResult,
    WeeklyPlanResult,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_TEMPERATURE = 0.2
_TIMEOUT = 60.0


# ── Pydantic schemas para validar respuesta del LLM ──────────────────────────

_MEAL_PARSE_TEMPERATURE = 0.1


class _MealItemSchema(BaseModel):
    ingredient: str
    quantity_g: float
    calories_kcal: float
    protein_g: float | None = None


class _MealParseSchema(BaseModel):
    items: list[_MealItemSchema]
    meal_type_guess: str


class _DayMealsSchema(BaseModel):
    day: str
    lunch: str
    dinner: str


class _ShoppingItemSchema(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str
    estimated_price_ars: float


class _WeeklyPlanSchema(BaseModel):
    days: list[_DayMealsSchema]
    shopping_list: list[_ShoppingItemSchema]
    total_cost_ars: float
    cooking_day: str
    prep_steps: list[str]


# ─────────────────────────────────────────────────────────────────────────────

class DeepSeekAdapter(AIPlannerPort):
    """Adapter de DeepSeek — intercambiable con OpenAI, Anthropic u Ollama."""

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._llm_router = LLMRouter(api_key=api_key, base_url=base_url)

    async def _call_api(self, messages: list[dict]) -> tuple[str, int]:
        """Llama al LLMRouter con fallback chain y circuit breaker."""
        response = await self._llm_router.generate(
            task_type=TaskType.STRUCTURED_JSON,
            messages=messages,
            temperature=_TEMPERATURE,
            timeout=_TIMEOUT,
            response_format={"type": "json_object"},
        )
        return response.content, response.tokens_input + response.tokens_output

    async def generate_plan(self, context: PlanningContext) -> WeeklyPlanResult:
        """Genera un plan semanal Batch Cooking 1x5."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_context_prompt(context)},
            {"role": "user", "content": TASK_PROMPT},
        ]

        raw, tokens = await self._call_api(messages)

        # Validar JSON contra schema Pydantic (con retry si falla)
        for validation_attempt in range(2):
            try:
                parsed = _WeeklyPlanSchema.model_validate_json(raw)
                break
            except (ValidationError, json.JSONDecodeError) as exc:
                if validation_attempt == 0:
                    logger.warning("LLM response invalid — retrying with error context: %s", exc)
                    error_msg = f"Tu respuesta anterior era inválida: {exc}. Reintentá con JSON válido."
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content": error_msg})
                    raw, tokens = await self._call_api(messages)
                else:
                    raise ValueError(f"LLM retornó JSON inválido después de 2 intentos: {exc}") from exc

        return WeeklyPlanResult(
            days=[DayMeals(day=d.day, lunch=d.lunch, dinner=d.dinner) for d in parsed.days],
            shopping_list=[
                ShoppingItem(
                    ingredient_name=item.ingredient_name,
                    quantity=item.quantity,
                    unit=item.unit,
                    estimated_price_ars=item.estimated_price_ars,
                )
                for item in parsed.shopping_list
            ],
            total_cost_ars=parsed.total_cost_ars,
            cooking_day=parsed.cooking_day,
            prep_steps=parsed.prep_steps,
            tokens_used=tokens,
        )

    async def parse_meal_description(
        self,
        description: str,
        ingredient_catalog: list[str],
    ) -> dict:
        """Parsea una descripción de comida en texto libre y retorna ítems estructurados.

        Usa temperatura 0.1 para máxima determinismo. Retorna JSON validado con Pydantic.
        Si las cantidades no están especificadas estima porciones razonables.
        Usa el catálogo de ingredientes para mejorar la precisión de calorías y proteínas.
        """
        catalog_excerpt = ", ".join(ingredient_catalog[:80]) if ingredient_catalog else "ninguno"

        system_prompt = (
            "Sos un nutricionista experto en la dieta argentina. "
            "Tu tarea es parsear descripciones de comidas en texto libre y devolver JSON estructurado. "
            "Siempre respondé SOLO con JSON válido, sin texto adicional."
        )
        user_content = (
            f"Descripción de la comida: \"{description}\"\n\n"
            f"Ingredientes conocidos en la base de datos (usá estos nombres exactos si hay match): "
            f"{catalog_excerpt}\n\n"
            "Devolvé un JSON con este esquema exacto:\n"
            "{\n"
            '  "items": [\n'
            '    {"ingredient": "nombre", "quantity_g": 150.0, "calories_kcal": 195.0, "protein_g": 28.0}\n'
            "  ],\n"
            '  "meal_type_guess": "almuerzo"\n'
            "}\n\n"
            "Reglas:\n"
            "- meal_type_guess: 'desayuno' (antes de las 11h o contexto), 'almuerzo' (12-15h), "
            "'cena' (19-23h), 'snack' (colación entre comidas). Si no podés inferir, usá 'almuerzo'.\n"
            "- Si no se especifica la cantidad, estimá una porción típica argentina.\n"
            "- Calculá calories_kcal y protein_g por los gramos indicados (no por 100g).\n"
            "- Usá valores nutricionales precisos: arroz cocido=130kcal/100g/2.7g prot, "
            "pechuga pollo=165kcal/100g/31g prot, papa=87kcal/100g/1.9g prot.\n"
            "- protein_g puede ser null si no corresponde (ej. azúcar, aceite)."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": _MEAL_PARSE_TEMPERATURE,
            "response_format": {"type": "json_object"},
        }

        last_exc: Exception = RuntimeError("No attempt made")
        raw = ""
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    raw = data["choices"][0]["message"]["content"]
                    logger.info("DeepSeek parse_meal_description OK")
                    break
            except (httpx.TimeoutException, httpx.HTTPStatusError, KeyError) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "DeepSeek parse_meal_description attempt %d/%d failed: %s — retry in %ds",
                        attempt + 1, _MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
        else:
            raise RuntimeError(
                f"DeepSeek parse_meal_description failed after {_MAX_RETRIES} retries: {last_exc}"
            ) from last_exc

        # Validar con Pydantic, con un retry si la respuesta es inválida
        for validation_attempt in range(2):
            try:
                parsed = _MealParseSchema.model_validate_json(raw)
                break
            except (ValidationError, json.JSONDecodeError) as exc:
                if validation_attempt == 0:
                    logger.warning(
                        "parse_meal_description: respuesta inválida — reintentando: %s", exc
                    )
                    error_msg = (
                        f"Tu respuesta anterior era inválida: {exc}. "
                        "Reintentá con JSON estrictamente válido siguiendo el esquema."
                    )
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content": error_msg})
                    payload["messages"] = messages
                    try:
                        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                            response = await client.post(
                                f"{self._base_url}/chat/completions",
                                headers=headers,
                                json=payload,
                            )
                            response.raise_for_status()
                            data = response.json()
                            raw = data["choices"][0]["message"]["content"]
                    except (httpx.TimeoutException, httpx.HTTPStatusError, KeyError) as retry_exc:
                        raise ValueError(
                            f"parse_meal_description: fallo en retry de validación: {retry_exc}"
                        ) from retry_exc
                else:
                    raise ValueError(
                        f"parse_meal_description: JSON inválido después de 2 intentos: {exc}"
                    ) from exc

        return {
            "items": [item.model_dump() for item in parsed.items],
            "meal_type_guess": parsed.meal_type_guess,
        }

    async def suggest_swap(self, request: SwapRequest) -> SwapResult:
        """Swap via IA — en Fase 2A el SwapService lo resuelve localmente sin IA."""
        return SwapResult(original_ingredient_id=request.ingredient_id, suggestions=[])

    async def generate_text(self, system_prompt: str, user_content: str) -> str:
        """
        Llamada genérica al LLM para análisis de texto libre (ej. Mood & Food).
        Retorna el contenido de texto de la respuesta.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": _TEMPERATURE,
            "response_format": {"type": "json_object"},
        }
        last_exc: Exception = RuntimeError("No attempt made")
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info("DeepSeek generate_text OK")
                    return content
            except (httpx.TimeoutException, httpx.HTTPStatusError, KeyError) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"DeepSeek generate_text failed: {last_exc}") from last_exc

    async def analyze_invoice(
        self, photo_b64: str, prompt: str, vision_model: str = "deepseek-vl2"
    ) -> dict:
        """Analiza una foto de factura usando el modelo de visión de DeepSeek.

        Envía la imagen en base64 siguiendo el formato OpenAI-compatible de visión.
        Retorna el JSON parseado con store, date e items.
        """
        import json

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{photo_b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": vision_model,
            "messages": messages,
            "temperature": _TEMPERATURE,
            "response_format": {"type": "json_object"},
        }

        last_exc: Exception = RuntimeError("No attempt made")
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info("DeepSeek analyze_invoice OK")
                    return json.loads(content)
            except (httpx.TimeoutException, httpx.HTTPStatusError, KeyError) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
            except json.JSONDecodeError as exc:
                raise ValueError(f"DeepSeek retornó JSON inválido en factura: {exc}") from exc

        raise RuntimeError(f"DeepSeek analyze_invoice failed: {last_exc}") from last_exc
