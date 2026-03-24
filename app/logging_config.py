"""
Configuración centralizada de logging para SGAI.

- Desarrollo: DEBUG, output a consola con formato detallado.
- Producción: INFO, output a consola (Railway captura stdout).
- Módulos ruidosos (sqlalchemy, httpx, apscheduler) en WARNING.
- Nuestros módulos (app.*) en DEBUG/INFO según entorno.
"""

import logging
import logging.config


def setup_logging(log_level: str = "INFO", app_env: str = "development") -> None:
    """Configura el logging global de la aplicación."""

    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": fmt,
                "datefmt": datefmt,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # Módulos ruidosos → solo WARNING
            "sqlalchemy.engine": {"level": "WARNING", "propagate": False, "handlers": ["console"]},
            "sqlalchemy.pool": {"level": "WARNING", "propagate": False, "handlers": ["console"]},
            "httpx": {"level": "WARNING", "propagate": False, "handlers": ["console"]},
            "httpcore": {"level": "WARNING", "propagate": False, "handlers": ["console"]},
            "apscheduler": {"level": "WARNING", "propagate": False, "handlers": ["console"]},
            "telegram": {"level": "WARNING", "propagate": False, "handlers": ["console"]},
            # Nuestros módulos → nivel configurado
            "app": {
                "level": "DEBUG" if app_env == "development" else log_level,
                "propagate": False,
                "handlers": ["console"],
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(config)
