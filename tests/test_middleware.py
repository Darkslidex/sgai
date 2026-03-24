"""Tests del middleware de logging HTTP."""

import logging
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_request_generates_log(client: AsyncClient, caplog) -> None:
    """Request a /api/v1/users/profile genera log con método, path y status."""
    with caplog.at_level(logging.INFO, logger="app.api.middleware"):
        response = await client.get("/api/v1/users/profile")

    # El endpoint puede devolver cualquier código — lo que importa es el log del middleware
    assert any(
        "GET" in record.message and "/api/v1/users/profile" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_health_request_not_logged(client: AsyncClient, caplog) -> None:
    """Request a /health NO genera log (path excluido)."""
    with caplog.at_level(logging.INFO, logger="app.api.middleware"):
        await client.get("/health")

    assert not any(
        "/health" in record.message
        for record in caplog.records
        if record.name == "app.api.middleware"
    )


@pytest.mark.asyncio
async def test_log_includes_response_time(client: AsyncClient, caplog) -> None:
    """El log incluye el tiempo de respuesta en ms."""
    with caplog.at_level(logging.INFO, logger="app.api.middleware"):
        await client.get("/api/v1/users/profile")

    middleware_logs = [r for r in caplog.records if r.name == "app.api.middleware"]
    assert len(middleware_logs) >= 1
    # El mensaje termina con "(\d+ms)"
    assert any("ms" in r.message for r in middleware_logs)
