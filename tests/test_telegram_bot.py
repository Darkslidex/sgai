"""Tests de los handlers del bot de Telegram (con mocks de DB y PTB)."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.telegram.bot import (
    cmd_ayuda,
    cmd_estado,
    cmd_precio,
    cmd_salud,
    cmd_start,
)


def _make_update(chat_id: int = 6513721904, text: str = "") -> MagicMock:
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = chat_id
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_context(args: list[str] | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.bot = AsyncMock()
    ctx.args = args or []
    return ctx


def _make_settings(allowed: list[int] = None) -> MagicMock:
    s = MagicMock()
    s.telegram_allowed_chat_ids = allowed or [6513721904]
    return s


@asynccontextmanager
async def _null_session():
    """Context manager que yields None (para reemplazar get_session)."""
    yield MagicMock()


# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_no_profile():
    """/start con usuario sin perfil → mensaje de bienvenida con /setup."""
    update = _make_update()

    mock_repo = AsyncMock()
    mock_repo.get_profile_by_chat_id.return_value = None

    with (
        patch("app.adapters.telegram.security.get_settings", return_value=_make_settings()),
        patch("app.adapters.telegram.bot.get_session", return_value=_null_session()),
        patch("app.adapters.telegram.bot.UserRepository", return_value=mock_repo),
        patch("app.adapters.telegram.bot.log_interaction", new=AsyncMock()),
    ):
        await cmd_start(update, _make_context())

    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "/setup" in msg


@pytest.mark.asyncio
async def test_estado_with_profile():
    """/estado con perfil existente → muestra resumen completo."""
    update = _make_update()

    mock_profile = MagicMock()
    mock_profile.id = 1
    mock_profile.name = "Felix"

    mock_user_repo = AsyncMock()
    mock_user_repo.get_profile_by_chat_id.return_value = mock_profile

    mock_health_repo = AsyncMock()
    mock_health_repo.get_latest_log.return_value = None

    mock_market_repo = AsyncMock()
    mock_market_repo.get_pantry.return_value = []
    mock_market_repo.get_all_current_prices.return_value = []

    mock_plan_repo = AsyncMock()
    mock_plan_repo.get_active_plan.return_value = None

    with (
        patch("app.adapters.telegram.security.get_settings", return_value=_make_settings()),
        patch("app.adapters.telegram.bot.get_session", return_value=_null_session()),
        patch("app.adapters.telegram.bot.UserRepository", return_value=mock_user_repo),
        patch("app.adapters.telegram.bot.HealthRepository", return_value=mock_health_repo),
        patch("app.adapters.telegram.bot.MarketRepository", return_value=mock_market_repo),
        patch("app.adapters.telegram.bot.PlanningRepository", return_value=mock_plan_repo),
        patch("app.adapters.telegram.bot.log_interaction", new=AsyncMock()),
    ):
        await cmd_estado(update, _make_context())

    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "Perfil" in msg
    assert "alacena" in msg.lower() or "Items" in msg


@pytest.mark.asyncio
async def test_ayuda_lists_commands():
    """/ayuda → respuesta contiene los comandos principales."""
    update = _make_update()

    with (
        patch("app.adapters.telegram.security.get_settings", return_value=_make_settings()),
        patch("app.adapters.telegram.bot.log_interaction", new=AsyncMock()),
    ):
        await cmd_ayuda(update, _make_context())

    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    for cmd in ["/start", "/perfil", "/setup", "/salud", "/precio", "/pantry", "/estado"]:
        assert cmd in msg


@pytest.mark.asyncio
async def test_salud_registers_and_confirms():
    """/salud sueno:7 estres:bajo registra y responde con confirmación."""
    update = _make_update()

    mock_user_repo = AsyncMock()
    mock_profile = MagicMock()
    mock_profile.id = 1
    mock_profile.weight_kg = 80.0
    mock_profile.height_cm = 175.0
    mock_profile.age = 42
    mock_profile.activity_level = "moderate"
    mock_user_repo.get_profile_by_chat_id.return_value = mock_profile

    mock_health_repo = AsyncMock()
    mock_health_repo.log_health.return_value = MagicMock()

    with (
        patch("app.adapters.telegram.security.get_settings", return_value=_make_settings()),
        patch("app.adapters.telegram.bot.get_session", return_value=_null_session()),
        patch("app.adapters.telegram.bot.UserRepository", return_value=mock_user_repo),
        patch("app.adapters.telegram.bot.HealthRepository", return_value=mock_health_repo),
        patch("app.adapters.telegram.bot.log_interaction", new=AsyncMock()),
    ):
        await cmd_salud(update, _make_context(args=["sueno:7", "estres:bajo"]))

    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "✅" in msg
    mock_health_repo.log_health.assert_called_once()


@pytest.mark.asyncio
async def test_precio_formats_ars():
    """/precio tomate 1500 → respuesta con precio formateado en ARS."""
    update = _make_update()

    mock_ing_repo = AsyncMock()
    mock_ingredient = MagicMock()
    mock_ingredient.id = 1
    mock_ingredient.name = "tomate"
    mock_ingredient.unit = "kg"
    mock_ing_repo.search_ingredients.return_value = [mock_ingredient]

    mock_market_repo = AsyncMock()
    mock_market_repo.add_price.return_value = MagicMock()

    with (
        patch("app.adapters.telegram.security.get_settings", return_value=_make_settings()),
        patch("app.adapters.telegram.bot.get_session", return_value=_null_session()),
        patch("app.adapters.telegram.bot.IngredientRepository", return_value=mock_ing_repo),
        patch("app.adapters.telegram.bot.MarketRepository", return_value=mock_market_repo),
        patch("app.adapters.telegram.bot.log_interaction", new=AsyncMock()),
    ):
        await cmd_precio(update, _make_context(args=["tomate", "1500"]))

    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "✅" in msg
    assert "1.500" in msg  # formato ARS con separador de miles
