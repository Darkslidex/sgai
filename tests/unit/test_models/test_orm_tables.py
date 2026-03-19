"""Tests de modelos ORM: creación de tablas y campo ADR-008."""

import pytest

import app.adapters.persistence.models  # noqa: F401 — fuerza registro de todos los ORM
from app.database import Base
from app.adapters.persistence.user_profile_orm import UserProfileORM


def test_all_10_tables_registered():
    """Las 10 tablas deben estar registradas en Base.metadata."""
    expected_tables = {
        "user_profiles",
        "health_logs",
        "recipes",
        "ingredients",
        "market_prices",
        "weekly_plans",
        "user_preferences",
        "recipe_ingredients",
        "pantry_items",
        "optimization_logs",
    }
    registered = set(Base.metadata.tables.keys())
    assert expected_tables == registered, f"Tablas faltantes: {expected_tables - registered}"


def test_adr008_max_storage_volume_column():
    """ADR-008: max_storage_volume existe, es nullable y tiene el comment correcto."""
    col = UserProfileORM.__table__.c.max_storage_volume
    assert col.nullable is True
    assert "ADR-008" in (col.comment or "")


@pytest.mark.asyncio
async def test_tables_created_in_sqlite(test_db_session):
    """Base.metadata.create_all crea las 10 tablas (verifica vía conftest SQLite)."""
    from sqlalchemy import text
    result = await test_db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    )
    tables = {row[0] for row in result.fetchall()}
    expected = {
        "user_profiles", "health_logs", "recipes", "ingredients",
        "market_prices", "weekly_plans", "user_preferences",
        "recipe_ingredients", "pantry_items", "optimization_logs",
    }
    assert expected.issubset(tables), f"Tablas faltantes en SQLite: {expected - tables}"
