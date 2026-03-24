"""Dependencias de autenticación para endpoints de SGAI."""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

_ana_key_header = APIKeyHeader(name="X-Ana-Key", auto_error=False)


async def verify_ana_api_key(key: str | None = Security(_ana_key_header)) -> None:
    """Verifica que la request viene de Ana usando su API key.

    Si ANA_API_KEY no está configurada en el .env, el endpoint queda bloqueado
    para evitar acceso no autenticado accidental.
    """
    settings = get_settings()

    if not settings.ana_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANA_API_KEY no configurada en el servidor.",
        )

    if key != settings.ana_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida.",
        )
