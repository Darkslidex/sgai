"""Tests del cliente HTTP del Dashboard SGAI."""

from unittest.mock import patch, MagicMock

import httpx
import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Instancia del SGAIClient con base URL de test."""
    from dashboard.components.api_client import SGAIClient
    return SGAIClient(base_url="http://testserver")


# ── get_profile ───────────────────────────────────────────────────────────────

def test_get_profile_returns_user_data(client):
    """get_profile retorna datos del usuario cuando la API responde 200."""
    payload = {
        "id": 1,
        "name": "Chef",
        "age": 35,
        "weight_kg": 80.0,
        "height_cm": 175.0,
        "activity_level": "active",
        "goal": "maintain",
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "get", return_value=mock_response):
        result = client.get_profile(user_id=1)

    assert result == payload
    assert result["name"] == "Chef"


# ── get_active_plan ───────────────────────────────────────────────────────────

def test_get_active_plan_returns_none_when_no_plan(client):
    """get_active_plan retorna None si la API responde 404."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=mock_response
    )

    with patch.object(client._client, "get", return_value=mock_response):
        result = client.get_active_plan(user_id=1)

    assert result is None


# ── Timeout handling ──────────────────────────────────────────────────────────

def test_client_handles_timeout_without_crashing(client):
    """El cliente retorna None en timeout sin lanzar excepción."""
    with patch.object(client._client, "get", side_effect=httpx.TimeoutException("timeout")):
        result = client.get_profile(user_id=1)

    assert result is None


# ── HTTP 500 handling ─────────────────────────────────────────────────────────

def test_client_handles_http_500(client):
    """El cliente retorna None en error 500 sin propagar la excepción."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=mock_response
    )

    with patch.object(client._client, "get", return_value=mock_response):
        result = client.get_profile(user_id=1)

    assert result is None


# ── is_api_reachable ──────────────────────────────────────────────────────────

def test_is_api_reachable_returns_true_on_200(client):
    """is_api_reachable retorna True cuando la API responde correctamente."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(client._client, "get", return_value=mock_response):
        assert client.is_api_reachable() is True


def test_is_api_reachable_returns_false_on_error(client):
    """is_api_reachable retorna False cuando la API no responde."""
    with patch.object(client._client, "get", side_effect=httpx.ConnectError("refused")):
        assert client.is_api_reachable() is False
