"""Tests del endpoint GET /health."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """GET /health debe retornar HTTP 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_has_required_fields(client: AsyncClient) -> None:
    """La respuesta debe contener los campos status, database y version."""
    response = await client.get("/health")
    body = response.json()
    assert "status" in body
    assert "database" in body
    assert "version" in body


@pytest.mark.asyncio
async def test_health_version_matches_config(client: AsyncClient) -> None:
    """La versión del response debe coincidir con la del config."""
    from app.config import get_settings
    settings = get_settings()
    response = await client.get("/health")
    assert response.json()["version"] == settings.app_version
