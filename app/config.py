"""Configuración centralizada de la aplicación usando Pydantic Settings v2.

Carga variables de entorno desde .env y las expone tipadas.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de SGAI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # === Base de Datos ===
    database_url: str = Field(..., description="URL de conexión async a PostgreSQL")

    # === DeepSeek API ===
    deepseek_api_key: str = Field(..., description="API key de DeepSeek")
    deepseek_base_url: str = Field(
        "https://api.deepseek.com/v1", description="URL base de la API de DeepSeek"
    )
    deepseek_model: str = Field("deepseek-chat", description="Modelo de DeepSeek a usar")
    deepseek_vision_model: str = Field("deepseek-vl2", description="Modelo de visión para procesar facturas")

    # === Telegram Bot ===
    telegram_bot_enabled: bool = Field(True, description="Activar/desactivar el bot de Telegram")
    telegram_bot_token: str | None = Field(None, description="Token del bot de Telegram")
    telegram_allowed_chat_ids: list[int] = Field(
        default_factory=list, description="Lista de chat IDs autorizados"
    )

    # === Seguridad ===
    jwt_secret_key: str = Field(..., description="Clave secreta para firmar JWTs")
    jwt_algorithm: str = Field("HS256", description="Algoritmo JWT")
    jwt_expiration_minutes: int = Field(30, description="Tiempo de expiración del JWT en minutos")
    encryption_key: str | None = Field(
        None,
        description=(
            "Clave Fernet para cifrado de datos sensibles. "
            "Generar con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        ),
    )

    # === App ===
    app_env: Literal["development", "staging", "production"] = Field(
        "development", description="Entorno de ejecución"
    )
    app_debug: bool = Field(False, description="Modo debug")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", description="Nivel de logging"
    )

    # Versión de la aplicación (no viene del .env)
    app_version: str = "0.1.0"

    @field_validator("telegram_allowed_chat_ids", mode="before")
    @classmethod
    def parse_chat_ids(cls, v: str | list | int | None) -> list[int]:
        """Parsea TELEGRAM_ALLOWED_CHAT_IDS desde string CSV, int o lista."""
        if v is None:
            return []
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            return [int(chat_id.strip()) for chat_id in v.split(",") if chat_id.strip()]
        return [int(item) for item in v]


def get_settings() -> Settings:
    """Retorna la instancia de Settings (puede ser cacheada con lru_cache en producción)."""
    return Settings()
