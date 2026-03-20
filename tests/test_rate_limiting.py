"""Tests del middleware de rate limiting."""

import pytest
from starlette.testclient import TestClient
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.middleware import RateLimitMiddleware


def _make_app(clear_store: bool = True) -> FastAPI:
    """Crea una app de test con RateLimitMiddleware."""
    if clear_store:
        RateLimitMiddleware._store.clear()

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/plan")
    async def plan_endpoint():
        return JSONResponse({"ok": True})

    @app.get("/api/v1/items")
    async def items_endpoint():
        return JSONResponse({"ok": True})

    return app


def test_ai_endpoint_blocks_after_10_requests():
    """11 requests rápidos a endpoint de IA → el 11vo retorna 429."""
    RateLimitMiddleware._store.clear()
    app = _make_app(clear_store=False)
    client = TestClient(app, raise_server_exceptions=False)

    for i in range(10):
        resp = client.get("/api/v1/plan")
        assert resp.status_code == 200, f"Request {i+1} debería ser 200"

    resp = client.get("/api/v1/plan")
    assert resp.status_code == 429
    assert "Demasiados intentos" in resp.json()["detail"]


def test_general_endpoint_allows_60_requests():
    """60 requests al endpoint general → todos 200."""
    RateLimitMiddleware._store.clear()
    app = _make_app(clear_store=False)
    client = TestClient(app, raise_server_exceptions=False)

    for i in range(60):
        resp = client.get("/api/v1/items")
        assert resp.status_code == 200, f"Request {i+1} debería ser 200"


def test_rate_limit_response_includes_retry_after():
    """La respuesta 429 incluye el header Retry-After."""
    RateLimitMiddleware._store.clear()
    app = _make_app(clear_store=False)
    client = TestClient(app, raise_server_exceptions=False)

    for _ in range(10):
        client.get("/api/v1/plan")

    resp = client.get("/api/v1/plan")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
