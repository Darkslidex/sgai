"""Entry point de la aplicación FastAPI.

Configura el lifespan, middleware y routers de SGAI.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1 import router as v1_router
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

    # Iniciar bot de Telegram en background (silencioso si falla en tests)
    bot_app = None
    try:
        from app.adapters.telegram.bot import create_telegram_bot

        bot_app = create_telegram_bot()
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        logger.info("Telegram bot started (polling)")
    except Exception as exc:
        logger.warning("Telegram bot not started: %s", exc)
        bot_app = None

    yield

    # Detener bot
    if bot_app is not None:
        try:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
            logger.info("Telegram bot stopped")
        except Exception as exc:
            logger.warning("Telegram bot shutdown error: %s", exc)

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
    app.include_router(v1_router)

    return app


app = create_app()
