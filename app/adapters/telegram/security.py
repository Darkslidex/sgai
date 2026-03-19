"""
Middleware de seguridad para el bot de Telegram.
PRIMERA LÍNEA DE DEFENSA: rechaza cualquier mensaje de chat_ids no autorizados.
"""

import functools
import logging
from collections.abc import Callable
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from app.config import get_settings

logger = logging.getLogger(__name__)


def authorized_only(func: Callable) -> Callable:
    """
    Decorator que verifica que el chat_id del update esté en la whitelist.

    - Si NO está en la whitelist: loguea WARNING y descarta silenciosamente.
    - Si SÍ está en la whitelist: loguea DEBUG y procesa normalmente.
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        if update.effective_chat is None:
            logger.warning("Update without effective_chat discarded")
            return

        chat_id = update.effective_chat.id
        settings = get_settings()

        if chat_id not in settings.telegram_allowed_chat_ids:
            logger.warning("Unauthorized access attempt from chat_id=%s", chat_id)
            return  # Silencio total — no dar información al atacante

        logger.debug("Authorized request from chat_id=%s", chat_id)
        return await func(update, context)

    return wrapper
