"""Tests del middleware de seguridad del bot de Telegram."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.telegram.security import authorized_only


def _make_update(chat_id: int) -> MagicMock:
    """Crea un mock de Update con el chat_id dado."""
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = chat_id
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


def _make_context() -> MagicMock:
    ctx = MagicMock()
    ctx.bot = AsyncMock()
    return ctx


def _make_settings(allowed_ids: list[int]) -> MagicMock:
    s = MagicMock()
    s.telegram_allowed_chat_ids = allowed_ids
    return s


# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_authorized_chat_id_passes():
    """Mensaje de chat_id autorizado → el handler se ejecuta."""
    called = False

    @authorized_only
    async def handler(update, context):
        nonlocal called
        called = True

    update = _make_update(chat_id=6513721904)
    with patch(
        "app.adapters.telegram.security.get_settings",
        return_value=_make_settings([6513721904]),
    ):
        await handler(update, _make_context())

    assert called is True


@pytest.mark.asyncio
async def test_unauthorized_chat_id_rejected():
    """Mensaje de chat_id NO autorizado → handler NO se ejecuta (silencio total)."""
    called = False

    @authorized_only
    async def handler(update, context):
        nonlocal called
        called = True

    update = _make_update(chat_id=9999999)
    with patch(
        "app.adapters.telegram.security.get_settings",
        return_value=_make_settings([6513721904]),
    ):
        await handler(update, _make_context())

    assert called is False
    # Verificar que NO se envió ninguna respuesta al atacante
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_unauthorized_generates_warning_log(caplog):
    """Intento no autorizado genera un log de nivel WARNING."""

    @authorized_only
    async def handler(update, context):
        pass

    update = _make_update(chat_id=1234567)
    with patch(
        "app.adapters.telegram.security.get_settings",
        return_value=_make_settings([6513721904]),
    ):
        with caplog.at_level(logging.WARNING, logger="app.adapters.telegram.security"):
            await handler(update, _make_context())

    assert any("1234567" in record.message for record in caplog.records)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


@pytest.mark.asyncio
async def test_multiple_allowed_chat_ids_all_pass():
    """Whitelist con múltiples IDs: todos pasan, los demás no."""
    allowed = [111, 222, 333]
    results = {}

    @authorized_only
    async def handler(update, context):
        results[update.effective_chat.id] = True

    with patch(
        "app.adapters.telegram.security.get_settings",
        return_value=_make_settings(allowed),
    ):
        for cid in allowed:
            await handler(_make_update(cid), _make_context())

        # Chat no autorizado
        await handler(_make_update(999), _make_context())

    assert results == {111: True, 222: True, 333: True}
    assert 999 not in results
