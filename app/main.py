"""Entry point de la aplicación FastAPI.

Configura el lifespan, middleware y routers de SGAI.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.config import get_settings
from app.database import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicación."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    init_db(settings.database_url)
    logger.info("SGAI started in %s mode", settings.app_env)

    yield

    await close_db()
    logger.info("SGAI shut down.")


def create_app() -> FastAPI:
    """Factory de la aplicación FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title="SGAI",
        description="Sistema de Gestión Alimenticia Inteligente",
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)

    return app


app = create_app()
