"""Configuración del Dashboard SGAI."""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class DashboardSettings(BaseSettings):
    api_base_url: str = "http://localhost:8000"
    dashboard_user: str = "chef"
    # bcrypt hash de la contraseña del dashboard (generado con bcrypt.hashpw)
    dashboard_password_hash: str = ""
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_minutes: int = 5
    # ID del usuario SGAI (sistema single-user)
    sgai_user_id: int = 1

    model_config = {"env_file": os.path.join(os.path.dirname(__file__), "..", ".env"), "extra": "ignore"}


@lru_cache(maxsize=1)
def get_dashboard_settings() -> DashboardSettings:
    return DashboardSettings()
