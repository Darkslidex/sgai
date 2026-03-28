"""Servicio de alertas automáticas de SGAI → Telegram.

Monitorea condiciones de salud del sistema y envía alertas proactivas.
Se ejecuta cada 15 minutos via APScheduler (configurado en main.py).
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Umbrales configurables
TOKENS_DAILY_ALERT = 50_000
ERROR_RATE_THRESHOLD = 0.05   # 5%
CONSECUTIVE_SYNC_FAILURES = 2
CONSECUTIVE_VALIDATION_FAILURES = 3


async def check_and_alert() -> None:
    """Verifica condiciones de alerta y envía notificaciones Telegram si se cumplen."""
    from app.database import get_session

    async with get_session() as session:
        alerts: list[str] = []

        # 1. Tokens diarios
        try:
            from sqlalchemy import text
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            result = await session.execute(
                text("SELECT COALESCE(SUM(tokens_input + tokens_output), 0) FROM llm_usage_log WHERE timestamp >= :since"),
                {"since": today},
            )
            tokens = result.scalar() or 0
            if tokens >= TOKENS_DAILY_ALERT:
                alerts.append(f"⚠️ Consumo alto de tokens hoy: {tokens:,} (límite: {TOKENS_DAILY_ALERT:,})")
        except Exception as e:
            logger.debug("Alert check tokens: %s", e)

        # 2. Error rate en la última hora
        try:
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            result = await session.execute(
                text("SELECT COUNT(*), SUM(CASE WHEN success THEN 0 ELSE 1 END) FROM llm_usage_log WHERE timestamp >= :since"),
                {"since": hour_ago},
            )
            row = result.fetchone()
            if row and row[0] and row[0] > 0:
                error_rate = (row[1] or 0) / row[0]
                if error_rate > ERROR_RATE_THRESHOLD:
                    alerts.append(f"🔴 Error rate LLM elevado: {error_rate:.1%} en la última hora")
        except Exception as e:
            logger.debug("Alert check error rate: %s", e)

        # 3. Circuit breaker abierto (3+ fallos consecutivos recientes)
        try:
            recent = datetime.utcnow() - timedelta(minutes=30)
            result = await session.execute(
                text(
                    "SELECT model, COUNT(*) as fails FROM llm_usage_log "
                    "WHERE timestamp >= :since AND success = false "
                    "GROUP BY model HAVING COUNT(*) >= 3"
                ),
                {"since": recent},
            )
            for row in result.fetchall():
                alerts.append(f"🔴 Circuit breaker posiblemente abierto para: {row[0]} ({row[1]} fallos recientes)")
        except Exception as e:
            logger.debug("Alert check circuit breaker: %s", e)

        if alerts:
            await _send_telegram_alerts(alerts)


async def _send_telegram_alerts(alerts: list[str]) -> None:
    """Envía las alertas al chat de Félix vía Telegram."""
    import httpx
    from app.config import get_settings

    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_allowed_chat_ids:
        logger.warning("Telegram no configurado para alertas del sistema")
        return

    text_msg = "🤖 *SGAI — Alerta del Sistema*\n\n" + "\n".join(alerts)

    for chat_id in settings.telegram_allowed_chat_ids:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": text_msg, "parse_mode": "Markdown"},
                )
            logger.info("Alerta del sistema enviada a chat_id=%s", chat_id)
        except Exception as e:
            logger.warning("No se pudo enviar alerta Telegram: %s", e)
