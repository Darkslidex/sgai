"""Despachador de alertas salientes de SGAI.

Implementa el patrón Circuit Breaker para alertas proactivas:
1. Intenta enviar a Ana (OpenClaw) vía POST al gateway.
2. Si Ana no está disponible, cae automáticamente a Telegram directo.

Para tareas internas (ej. solicitud de scraping a Ana), no hay fallback:
si Ana está caída simplemente se loguea el fallo.
"""

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_ANA_TIMEOUT_SECONDS = 5


async def dispatch_alert(
    alert_type: str,
    data: dict[str, Any],
    instructions: str,
    *,
    fallback_chat_id: str | None = None,
    fallback_message: str | None = None,
) -> str:
    """Envía una alerta a Ana con fallback a Telegram si Ana está caída.

    Args:
        alert_type: Tipo de alerta ("expiry_alert", "waste_risk", "price_request").
        data: Payload estructurado con los datos de la alerta.
        instructions: Texto natural para que Ana entienda qué hacer.
        fallback_chat_id: Si se provee y Ana falla, se usa como destino Telegram.
        fallback_message: Mensaje de texto plano para el fallback Telegram.

    Returns:
        "ana" si la alerta llegó a Ana, "telegram_fallback" si se usó Telegram,
        "no_channel" si ninguno estaba disponible.
    """
    settings = get_settings()

    # ── Intentar Ana primero ──────────────────────────────────────────────────
    if settings.openclaw_webhook_url and settings.sgai_outbound_key:
        payload = {
            "type": alert_type,
            "data": data,
            "instructions": instructions,
        }
        try:
            async with httpx.AsyncClient(timeout=_ANA_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    settings.openclaw_webhook_url,
                    json=payload,
                    headers={"X-SGAI-Key": settings.sgai_outbound_key},
                )
            if response.is_success:
                logger.info("Alerta '%s' enviada a Ana (HTTP %d).", alert_type, response.status_code)
                return "ana"
            logger.warning(
                "Ana respondió HTTP %d para alerta '%s'. Activando fallback.",
                response.status_code,
                alert_type,
            )
        except httpx.TimeoutException:
            logger.warning("Ana no respondió en %ds (alerta '%s'). Activando fallback.", _ANA_TIMEOUT_SECONDS, alert_type)
        except Exception as exc:
            logger.warning("Error al contactar Ana (alerta '%s'): %s. Activando fallback.", alert_type, exc)
    else:
        logger.debug("OPENCLAW_WEBHOOK_URL o SGAI_OUTBOUND_KEY no configurados — saltando Ana.")

    # ── Fallback: Telegram directo ────────────────────────────────────────────
    if fallback_chat_id and fallback_message:
        await _send_telegram_direct(fallback_chat_id, fallback_message)
        logger.info("Alerta '%s' enviada por Telegram directo a chat_id=%s.", alert_type, fallback_chat_id)
        return "telegram_fallback"

    logger.warning("Alerta '%s' sin canal disponible (Ana caída, sin fallback configurado).", alert_type)
    return "no_channel"


async def dispatch_task_to_ana(
    task_type: str,
    data: dict[str, Any],
    instructions: str,
) -> bool:
    """Envía una tarea a Ana (sin fallback). Para tareas internas como solicitudes de scraping.

    Returns:
        True si Ana recibió la tarea, False si no estaba disponible.
    """
    settings = get_settings()

    if not settings.openclaw_webhook_url or not settings.sgai_outbound_key:
        logger.debug("OPENCLAW_WEBHOOK_URL no configurado — tarea '%s' no enviada a Ana.", task_type)
        return False

    payload = {
        "type": task_type,
        "data": data,
        "instructions": instructions,
    }
    try:
        async with httpx.AsyncClient(timeout=_ANA_TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.openclaw_webhook_url,
                json=payload,
                headers={"X-SGAI-Key": settings.sgai_outbound_key},
            )
        if response.is_success:
            logger.info("Tarea '%s' enviada a Ana (HTTP %d).", task_type, response.status_code)
            return True
        logger.warning("Ana respondió HTTP %d para tarea '%s'.", response.status_code, task_type)
        return False
    except Exception as exc:
        logger.warning("No se pudo enviar tarea '%s' a Ana: %s.", task_type, exc)
        return False


async def _send_telegram_direct(chat_id: str, text: str) -> None:
    """Envía un mensaje directo vía Telegram Bot API (canal de emergencia)."""
    settings = get_settings()

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN no configurado — no se puede enviar fallback a chat_id=%s.", chat_id)
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
    except Exception as exc:
        logger.warning("Fallback Telegram también falló para chat_id=%s: %s", chat_id, exc)
