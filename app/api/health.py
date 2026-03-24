"""Endpoint de health check para verificar el estado de la aplicación y la base de datos."""

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

# Momento de inicio de la aplicación (aproximado al import del módulo)
_start_time: float = time.monotonic()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Verifica el estado de la aplicación y la conexión a la base de datos.

    Siempre retorna 200 para evitar reinicios innecesarios de Railway.
    Solo retorna 503 si el sistema está completamente inutilizable.
    """
    settings = get_settings()
    uptime = int(time.monotonic() - _start_time)

    db_info: dict = {"status": "disconnected"}
    overall_status = "degraded"

    try:
        await db.execute(text("SELECT 1"))
        db_info["status"] = "connected"
        overall_status = "healthy"
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        db_info["detail"] = str(exc)

    # Contar tablas (best-effort; falla silenciosamente en SQLite)
    try:
        result = await db.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        db_info["tables"] = result.scalar()
    except Exception:
        pass  # SQLite no tiene information_schema — ignorar en tests

    return {
        "status": overall_status,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": db_info,
        "uptime_seconds": uptime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
