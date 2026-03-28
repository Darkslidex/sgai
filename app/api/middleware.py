"""
Middleware de logging HTTP para SGAI.

Loguea método, path, status code y tiempo de respuesta de cada request.
Excluye /health para no saturar los logs.
No loguea bodies para evitar exponer datos sensibles.
"""

import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_EXCLUDED_PATHS = {"/health"}

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Endpoints de IA (costo por token): 10 req/hora
_AI_PATH_PREFIXES = ("/api/v1/plan", "/api/v1/swap")
# Rate limit tiers: (max_requests, window_seconds)
_WEBHOOK_PATH_PREFIX = "/api/v1/webhooks"
_TIERS = {
    "ai": (10, 3600),
    "webhook": (60, 60),   # 60 req/min para webhooks de Ana
    "general": (60, 60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting en memoria por IP.
    - Endpoints de IA (/api/v1/plan, /api/v1/swap): 10 req/hora
    - API general: 60 req/minuto
    NOTA para producción: reemplazar _store por Redis para multi-worker.
    """

    _store: dict[str, list[float]] = {}  # {"ip:tier": [timestamps]}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if any(path.startswith(p) for p in _AI_PATH_PREFIXES):
            tier = "ai"
        elif path.startswith(_WEBHOOK_PATH_PREFIX):
            tier = "webhook"
        else:
            tier = "general"
        max_requests, window_seconds = _TIERS[tier]
        key = f"{client_ip}:{tier}"
        now = time.monotonic()

        timestamps = self._store.get(key, [])
        timestamps = [t for t in timestamps if now - t < window_seconds]

        if len(timestamps) >= max_requests:
            wait_time = max(1, int(window_seconds - (now - timestamps[0])))
            logger.warning("Rate limit exceeded: %s tier=%s", client_ip, tier)
            return Response(
                content=json.dumps(
                    {"detail": f"Demasiados intentos. Esperá {wait_time} segundos."}
                ),
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(wait_time)},
            )

        timestamps.append(now)
        self._store[key] = timestamps
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Loguea cada request HTTP: método, path, status code y tiempo en ms."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "%s %s → %s (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


class AnaAuditMiddleware(BaseHTTPMiddleware):
    """Registra en DB cada request autenticado con X-Ana-Key para audit trail."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Solo auditar requests con X-Ana-Key
        if not request.headers.get("X-Ana-Key"):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Fire-and-forget: no bloqueamos la respuesta por el log
        try:
            from datetime import datetime
            from app.database import get_session
            from app.adapters.persistence.ana_access_log_orm import AnaAccessLogORM

            async def _log():
                async with get_session() as session:
                    entry = AnaAccessLogORM(
                        timestamp=datetime.utcnow(),
                        endpoint=request.url.path,
                        method=request.method,
                        response_code=response.status_code,
                        response_time_ms=elapsed_ms,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent", "")[:300],
                    )
                    session.add(entry)
                    await session.commit()

            import asyncio
            asyncio.create_task(_log())
        except Exception:
            pass  # No interrumpir la respuesta por fallo en audit log

        return response
