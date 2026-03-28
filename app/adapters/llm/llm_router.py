"""
LLMRouter — capa de abstracción multi-LLM con fallback chain y circuit breaker.

Selecciona el modelo óptimo según tipo de tarea. Si el primero falla,
intenta con los siguientes en la cadena. Registra todo en llm_usage_log.
"""

import logging
import time
from enum import Enum
from typing import Dict, Optional

import httpx
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class TaskType(Enum):
    STRUCTURED_JSON = "structured_json"   # Planes de comida, listas de compras
    CONVERSATIONAL = "conversational"     # Respuestas de Ana
    ANALYSIS = "analysis"                 # Insights Mood&Food, correlaciones


class LLMResponse(BaseModel):
    content: str
    model_used: str
    tokens_input: int
    tokens_output: int
    latency_ms: float
    fallback_used: bool = False


class CircuitBreaker:
    def __init__(self, max_failures: int = 3, cooldown_seconds: int = 600) -> None:
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self.failures: Dict[str, int] = {}
        self.last_failure: Dict[str, float] = {}

    def is_open(self, model: str) -> bool:
        if model not in self.failures:
            return False
        if self.failures[model] >= self.max_failures:
            elapsed = time.time() - self.last_failure.get(model, 0)
            if elapsed < self.cooldown_seconds:
                return True
            self.failures[model] = 0  # Reset after cooldown
        return False

    def record_failure(self, model: str) -> None:
        self.failures[model] = self.failures.get(model, 0) + 1
        self.last_failure[model] = time.time()

    def record_success(self, model: str) -> None:
        self.failures[model] = 0

    def get_status(self) -> dict:
        """Retorna el estado de todos los circuit breakers."""
        status = {}
        for model in set(list(self.failures.keys()) + list(self.last_failure.keys())):
            status[model] = "open" if self.is_open(model) else "closed"
        return status


class LLMRouter:
    """
    Selecciona el modelo óptimo según tipo de tarea.
    Fallback chain automático con circuit breaker.
    """

    CHAINS: dict[TaskType, list[str]] = {
        TaskType.STRUCTURED_JSON: [
            "xiaomi/mimo-v2-flash",
            "google/gemini-2.5-flash",
            "meta-llama/llama-4-maverick",
        ],
        TaskType.CONVERSATIONAL: [
            "google/gemini-2.5-flash-preview-05-20",
            "google/gemini-2.5-flash",
            "meta-llama/llama-4-maverick",
        ],
        TaskType.ANALYSIS: [
            "xiaomi/mimo-v2-flash",
            "google/gemini-2.5-flash",
        ],
    }

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        max_failures: int = 3,
        cooldown_seconds: int = 600,
        default_timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.circuit_breaker = CircuitBreaker(max_failures, cooldown_seconds)
        self.default_timeout = default_timeout

    async def generate(
        self,
        task_type: TaskType,
        messages: list,
        temperature: float = 0.2,
        timeout: Optional[float] = None,
        response_format: Optional[dict] = None,
        log_to_db: bool = True,
    ) -> LLMResponse:
        """Genera una respuesta usando el mejor modelo disponible de la cadena."""
        chain = self.CHAINS[task_type]
        timeout = timeout or self.default_timeout

        for model in chain:
            if self.circuit_breaker.is_open(model):
                logger.warning("Circuit breaker OPEN para %s, saltando", model)
                continue

            start = time.time()
            try:
                payload: dict = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if response_format:
                    payload["response_format"] = response_format

                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                latency = (time.time() - start) * 1000
                self.circuit_breaker.record_success(model)

                result = LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model_used=model,
                    tokens_input=data.get("usage", {}).get("prompt_tokens", 0),
                    tokens_output=data.get("usage", {}).get("completion_tokens", 0),
                    latency_ms=latency,
                    fallback_used=(model != chain[0]),
                )

                if log_to_db:
                    await self._log_usage(result, task_type, success=True)

                return result

            except Exception as exc:
                self.circuit_breaker.record_failure(model)
                latency = (time.time() - start) * 1000
                logger.error("LLM %s falló (%.0fms): %s", model, latency, exc)

                if log_to_db:
                    await self._log_usage_error(
                        model=model,
                        task_type=task_type,
                        latency_ms=latency,
                        error=str(exc),
                    )
                continue

        raise RuntimeError(
            f"Todos los LLMs fallaron para {task_type.value}. "
            "Verificá los circuit breakers en /api/v1/admin/llm-usage."
        )

    async def _log_usage(self, result: LLMResponse, task_type: TaskType, success: bool) -> None:
        """Registra el uso del LLM en la DB (fire-and-forget, no bloquea)."""
        try:
            from app.database import get_session
            from app.adapters.persistence.llm_usage_orm import LLMUsageLogORM
            from datetime import datetime

            async with get_session() as session:
                log = LLMUsageLogORM(
                    timestamp=datetime.utcnow(),
                    model=result.model_used,
                    task_type=task_type.value,
                    tokens_input=result.tokens_input,
                    tokens_output=result.tokens_output,
                    latency_ms=result.latency_ms,
                    success=success,
                    error_message=None,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.warning("No se pudo registrar uso LLM en DB: %s", e)

    async def _log_usage_error(
        self, model: str, task_type: TaskType, latency_ms: float, error: str
    ) -> None:
        """Registra un error de LLM en la DB."""
        try:
            from app.database import get_session
            from app.adapters.persistence.llm_usage_orm import LLMUsageLogORM
            from datetime import datetime

            async with get_session() as session:
                log = LLMUsageLogORM(
                    timestamp=datetime.utcnow(),
                    model=model,
                    task_type=task_type.value,
                    tokens_input=0,
                    tokens_output=0,
                    latency_ms=latency_ms,
                    success=False,
                    error_message=error[:500],
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.warning("No se pudo registrar error LLM en DB: %s", e)
