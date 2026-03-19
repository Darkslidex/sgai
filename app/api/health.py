"""Endpoint de health check para verificar el estado de la aplicación y la base de datos."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Verifica el estado de la aplicación y la conexión a la base de datos."""
    settings = get_settings()

    db_status = "disconnected"
    overall_status = "degraded"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
        overall_status = "healthy"
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)

    return {
        "status": overall_status,
        "database": db_status,
        "version": settings.app_version,
        "environment": settings.app_env,
    }
