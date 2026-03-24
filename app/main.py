"""Entry point de la aplicación FastAPI.

Configura el lifespan, middleware y routers de SGAI.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.error_handlers import register_error_handlers
from app.api.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.api.v1 import router as v1_router
from app.config import get_settings
from app.database import close_db, init_db
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicación."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level, app_env=settings.app_env)

    init_db(settings.database_url)
    logger.info("SGAI started in %s mode", settings.app_env)

    # ── APScheduler ──────────────────────────────────────────────────────────
    scheduler = AsyncIOScheduler()

    from app.adapters.backup import scheduled_backup

    # Backup diario a las 03:00 UTC
    scheduler.add_job(scheduled_backup, "cron", hour=3, minute=0, id="daily_backup")

    # Limpieza semanal de health_logs > 90 días (domingo 02:00 UTC)
    scheduler.add_job(
        _cleanup_old_health_logs,
        "cron",
        day_of_week="sun",
        hour=2,
        minute=0,
        id="weekly_health_cleanup",
    )

    # ETL Fase 3B — Precios + Vencimientos + Desperdicio
    # Actualizar precios SEPA diariamente a las 06:00 UTC
    scheduler.add_job(
        _etl_update_sepa_prices,
        "cron",
        hour=6,
        minute=0,
        id="daily_sepa_prices",
    )
    # Verificar vencimientos y notificar a las 08:00 UTC
    scheduler.add_job(
        _etl_check_expiry_and_notify,
        "cron",
        hour=8,
        minute=0,
        id="daily_expiry_check",
    )
    scheduler.start()
    logger.info("APScheduler started (backup 03:00 UTC, SEPA 06:00 UTC, expiry 08:00 UTC)")

    # ── Telegram Bot ──────────────────────────────────────────────────────────
    bot_app = None
    if settings.telegram_bot_enabled:
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
    else:
        logger.info("Telegram bot disabled (TELEGRAM_BOT_ENABLED=false)")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")

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


async def _send_telegram_notification(chat_id: str, text: str) -> None:
    """Envía una notificación vía Telegram Bot API usando httpx."""
    import httpx

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
    except Exception as exc:
        logger.warning("No se pudo enviar notificación Telegram a %s: %s", chat_id, exc)


async def _etl_update_sepa_prices() -> None:
    """ETL diario: actualiza precios SEPA para ingredientes del plan activo."""
    from sqlalchemy import text

    from app.adapters.persistence.ingredient_repo import IngredientRepository
    from app.adapters.persistence.market_repo import MarketRepository
    from app.adapters.persistence.planning_repo import PlanningRepository
    from app.adapters.persistence.user_repo import UserRepository
    from app.adapters.pricing.sepa_price_adapter import SEPAPriceAdapter
    from app.database import get_session

    logger.info("ETL: iniciando actualización de precios SEPA...")
    updated = 0

    async with get_session() as session:
        user_repo = UserRepository(session)
        # Sistema single-user: obtener el primer usuario activo
        result = await session.execute(text("SELECT id FROM user_profiles LIMIT 1"))
        row = result.fetchone()
        if row is None:
            logger.info("ETL SEPA: sin usuarios, saltando.")
            return
        user_id = row[0]

        planning_repo = PlanningRepository(session)
        active_plan = await planning_repo.get_active_plan(user_id)
        if active_plan is None:
            logger.info("ETL SEPA: sin plan activo para user_id=%d, saltando.", user_id)
            return

        market_repo = MarketRepository(session)
        ing_repo = IngredientRepository(session)
        all_ingredients = await ing_repo.list_ingredients()
        ingredient_names = {i.id: i.name for i in all_ingredients}

        sepa_adapter = SEPAPriceAdapter(market_repo, ingredient_names)

        # Actualizar solo ingredientes del plan activo
        items = active_plan.shopping_list_json.get("items", [])
        for item in items:
            name = item.get("ingredient_name", "")
            matches = await ing_repo.search_ingredients(name)
            if matches:
                price = await sepa_adapter.get_price(matches[0].id)
                if price:
                    updated += 1

    logger.info("ETL SEPA completado: %d precios actualizados.", updated)


async def _etl_check_expiry_and_notify() -> None:
    """ETL diario: verifica vencimientos de pantry y calcula waste risk. Notifica vía Telegram."""
    from sqlalchemy import text

    from app.adapters.persistence.ingredient_repo import IngredientRepository
    from app.adapters.persistence.market_repo import MarketRepository
    from app.adapters.persistence.planning_repo import PlanningRepository
    from app.database import get_session
    from app.domain.services.consumption_ratio_service import ConsumptionRatioService
    from app.domain.services.pantry_service import PantryService

    logger.info("ETL: verificando vencimientos y riesgo de desperdicio...")
    settings = get_settings()

    async with get_session() as session:
        result = await session.execute(
            text("SELECT id, telegram_chat_id FROM user_profiles LIMIT 1")
        )
        row = result.fetchone()
        if row is None:
            return
        user_id, chat_id = row[0], row[1]

        market_repo = MarketRepository(session)
        ing_repo = IngredientRepository(session)
        planning_repo = PlanningRepository(session)

        pantry_service = PantryService(market_repo, ing_repo)
        consumption_service = ConsumptionRatioService(market_repo, planning_repo, ing_repo)

        expiring = await pantry_service.get_expiring_soon(user_id, days=3)
        expired = await pantry_service.get_expired(user_id)
        waste_report = await consumption_service.get_waste_risk_report(user_id)
        at_risk = [w for w in waste_report if w.action == "will_waste"]

        lines: list[str] = []

        if expired:
            lines.append(f"🚨 *{len(expired)} item(s) vencidos* en tu alacena — descartálos.")

        if expiring:
            lines.append(f"⚠️ *{len(expiring)} item(s) próximos a vencer* (próximos 3 días):")
            for item in expiring[:5]:
                days_left = ""
                if item.expires_at:
                    from datetime import datetime
                    delta = item.expires_at - datetime.utcnow()
                    days_left = f" ({max(0, delta.days)} días)"
                lines.append(f"  • Ingrediente #{item.ingredient_id}: {item.quantity_amount} {item.unit}{days_left}")

        if at_risk:
            lines.append(f"\n⚠️ *{len(at_risk)} item(s) en riesgo de desperdicio* (consumo insuficiente):")
            for w in at_risk[:3]:
                lines.append(
                    f"  • Ingrediente #{w.pantry_item.ingredient_id}: "
                    f"{w.days_to_consume:.0f} días para consumir, "
                    f"{w.days_remaining} días restantes"
                )

        if lines:
            await _send_telegram_notification(chat_id, "\n".join(lines))
            logger.info("ETL expiry: notificación enviada a chat_id=%s.", chat_id)
        else:
            logger.info("ETL expiry: todo en orden, sin notificaciones.")


async def _cleanup_old_health_logs() -> None:
    """Elimina health_logs con más de 90 días para controlar el tamaño de la DB."""
    from sqlalchemy import text

    from app.database import get_session

    async with get_session() as session:
        result = await session.execute(
            text("DELETE FROM health_logs WHERE date < NOW() - INTERVAL '90 days'")
        )
        await session.commit()
        logger.info("Health logs cleanup: %d filas eliminadas", result.rowcount)


def create_app() -> FastAPI:
    """Factory de la aplicación FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title="SGAI",
        description="Sistema de Gestión Alimenticia Inteligente",
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(v1_router)

    register_error_handlers(app)

    return app


app = create_app()
