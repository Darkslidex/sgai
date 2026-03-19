"""Tests de API: registros de salud."""

from datetime import date, timedelta

import pytest

TODAY = str(date.today())
YESTERDAY = str(date.today() - timedelta(days=1))


@pytest.mark.asyncio
async def test_log_health_returns_201(client):
    """POST health log con source='manual' → 201."""
    resp = await client.post(
        "/api/v1/health/log",
        json={
            "user_id": 1,
            "date": TODAY,
            "sleep_score": 85.0,
            "stress_level": 3.0,
            "steps": 8000,
            "mood": "good",
            "source": "manual",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sleep_score"] == 85.0
    assert data["source"] == "manual"
    assert data["user_id"] == 1


@pytest.mark.asyncio
async def test_log_health_sleep_score_over_100_returns_422(client):
    """POST health log con sleep_score=150 → 422 (violación le=100)."""
    resp = await client.post(
        "/api/v1/health/log",
        json={
            "user_id": 1,
            "date": TODAY,
            "sleep_score": 150.0,
            "source": "manual",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_logs_with_date_range(client):
    """POST logs en dos fechas, GET con rango retorna ambos."""
    await client.post(
        "/api/v1/health/log",
        json={"user_id": 2, "date": TODAY, "sleep_score": 80.0, "source": "manual"},
    )
    await client.post(
        "/api/v1/health/log",
        json={"user_id": 2, "date": YESTERDAY, "sleep_score": 70.0, "source": "manual"},
    )

    resp = await client.get(
        f"/api/v1/health/logs/2?start={YESTERDAY}&end={TODAY}"
    )
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) == 2
    scores = {l["sleep_score"] for l in logs}
    assert 80.0 in scores
    assert 70.0 in scores
