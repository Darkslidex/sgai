"""Entorno de Alembic configurado para migraciones async con SQLAlchemy."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Importar modelos para que Alembic detecte cambios en autogenerate
import app.adapters.persistence.models  # noqa: F401
from app.database import Base

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Obtiene la URL de BD desde settings (sobreescribe alembic.ini)."""
    from app.config import get_settings
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo offline (genera SQL sin conectarse)."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Ejecuta migraciones con una conexión existente."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Ejecuta migraciones en modo online (conecta a la BD real)."""
    connectable = create_async_engine(get_database_url())
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
