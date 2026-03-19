"""Configuración de la base de datos async con SQLAlchemy.

Provee el engine async, la sessionmaker y la dependency `get_db` para FastAPI.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos ORM de la aplicación."""

    pass


def create_engine_from_url(database_url: str) -> Any:
    """Crea el engine async a partir de la URL de conexión."""
    return create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# Engine y sessionmaker se inicializan en el lifespan de la app
_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    """Inicializa el engine y la sessionmaker. Llamar en el lifespan startup."""
    global _engine, _async_session_factory
    _engine = create_engine_from_url(database_url)
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency de FastAPI que provee una sesión de base de datos por request."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager para obtener sesión DB fuera del contexto FastAPI (ej: bot de Telegram)."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    """Cierra el engine. Llamar en el lifespan shutdown."""
    if _engine is not None:
        await _engine.dispose()
