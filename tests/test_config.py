"""Tests de carga y validación de configuración."""

import os
import pytest
from pydantic import ValidationError


def test_settings_loads_with_env_vars() -> None:
    """Settings debe cargar correctamente con variables de entorno seteadas."""
    from app.config import Settings

    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        deepseek_api_key="test-key",
        telegram_bot_token="test-token",
        telegram_allowed_chat_ids=[123456789],
        jwt_secret_key="test-secret",
    )
    assert s.app_version == "0.1.0"
    assert s.app_env == "development"


def test_telegram_chat_ids_parses_csv_string() -> None:
    """TELEGRAM_ALLOWED_CHAT_IDS debe parsear '123,456' a [123, 456]."""
    from app.config import Settings

    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        deepseek_api_key="test-key",
        telegram_bot_token="test-token",
        telegram_allowed_chat_ids="123,456",  # type: ignore[arg-type]
        jwt_secret_key="test-secret",
    )
    assert s.telegram_allowed_chat_ids == [123, 456]


def test_app_env_rejects_invalid_values() -> None:
    """APP_ENV debe rechazar valores fuera de development/staging/production."""
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            deepseek_api_key="test-key",
            telegram_bot_token="test-token",
            telegram_allowed_chat_ids=[123],
            jwt_secret_key="test-secret",
            app_env="invalid_env",  # type: ignore[arg-type]
        )
