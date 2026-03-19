"""
Registro de auditoría de todas las interacciones del bot de Telegram.
Formato: [TIMESTAMP] [CHAT_ID] [COMMAND] [SUCCESS/FAIL] [DETAILS]
"""

import logging

logger = logging.getLogger("sgai.audit")


async def log_interaction(
    chat_id: int,
    command: str,
    success: bool,
    details: str = "",
) -> None:
    """
    Registra cada interacción del bot en el log de auditoría.

    - success=True  → nivel INFO
    - success=False → nivel WARNING
    """
    status = "SUCCESS" if success else "FAIL"
    message = "[CHAT_ID=%s] [CMD=%s] [%s] %s" % (chat_id, command, status, details)

    if success:
        logger.info(message)
    else:
        logger.warning(message)
