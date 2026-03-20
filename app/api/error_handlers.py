"""
Handlers globales de errores para FastAPI.
NUNCA expone stack traces ni detalles internos al usuario.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Registra todos los handlers de error en la aplicación FastAPI."""

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled error on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor. Contactá al administrador."},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return JSONResponse(
                status_code=404,
                content={"detail": "Recurso no encontrado."},
            )
        if exc.status_code == 429:
            retry_after = (exc.headers or {}).get("Retry-After", "60")
            return JSONResponse(
                status_code=429,
                content={"detail": f"Demasiados intentos. Esperá {retry_after} segundos."},
                headers=exc.headers or {},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error.get("loc", []))
            errors.append({"field": field, "message": error.get("msg", "Valor inválido")})
        return JSONResponse(
            status_code=422,
            content={"detail": "Error de validación", "errors": errors},
        )
