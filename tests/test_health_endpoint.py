"""Tests del endpoint GET /health (versión robusta con uptime, timestamp, tables)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200_when_db_ok(client: AsyncClient) -> None:
    """GET /health retorna HTTP 200 con status healthy cuando DB está OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_returns_200_when_db_down(client: AsyncClient) -> None:
    """GET /health retorna HTTP 200 con status degraded cuando DB está caída.

    Railway no debe reiniciar el proceso por un fallo de DB transitorio.
    """
    from unittest.mock import AsyncMock, patch
    from sqlalchemy.exc import OperationalError

    broken_db = AsyncMock()
    broken_db.execute.side_effect = OperationalError("conn", None, Exception("refused"))

    from app.database import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: broken_db

    from httpx import ASGITransport, AsyncClient as AC

    async with AC(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_includes_required_fields(client: AsyncClient) -> None:
    """El response incluye version, environment y timestamp."""
    response = await client.get("/health")
    body = response.json()
    assert "version" in body
    assert "environment" in body
    assert "timestamp" in body
    assert body["environment"] == "development"


@pytest.mark.asyncio
async def test_health_uptime_is_positive(client: AsyncClient) -> None:
    """uptime_seconds es un número positivo (>= 0)."""
    response = await client.get("/health")
    assert response.json()["uptime_seconds"] >= 0
