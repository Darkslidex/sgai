"""Tests para los adapters de salud: ManualHealthAdapter y HealthConnectAdapter."""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

from app.adapters.health.health_connect_adapter import HealthConnectAdapter
from app.adapters.health.manual_health_adapter import ManualHealthAdapter
from app.domain.models.health import HealthLog


# ── HealthConnectAdapter ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_connect_get_latest_raises_not_implemented():
    """HealthConnectAdapter.get_latest_metrics levanta NotImplementedError."""
    adapter = HealthConnectAdapter()
    with pytest.raises(NotImplementedError) as exc_info:
        await adapter.get_latest_metrics(user_id=1)
    assert "ADR-003" in str(exc_info.value)


@pytest.mark.asyncio
async def test_health_connect_get_metrics_range_raises_not_implemented():
    """HealthConnectAdapter.get_metrics_range levanta NotImplementedError."""
    adapter = HealthConnectAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.get_metrics_range(
            user_id=1,
            start=date(2026, 3, 1),
            end=date(2026, 3, 19),
        )


# ── ManualHealthAdapter ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manual_adapter_get_latest_returns_health_log():
    """ManualHealthAdapter.get_latest_metrics lee de HealthRepository."""
    expected_log = HealthLog(
        id=1, user_id=1,
        date=date(2026, 3, 19),
        sleep_score=75.0, stress_level=4.0, hrv=55.0,
        steps=8000, mood="good", notes=None, source="manual",
        created_at=datetime(2026, 3, 19),
    )

    # Mock de session + repo
    mock_session = MagicMock()
    adapter = ManualHealthAdapter(session=mock_session)
    adapter._repo = AsyncMock()
    adapter._repo.get_latest_log.return_value = expected_log

    result = await adapter.get_latest_metrics(user_id=1)
    assert result == expected_log
    adapter._repo.get_latest_log.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_manual_adapter_get_latest_returns_none_when_no_data():
    """ManualHealthAdapter retorna None si no hay logs."""
    mock_session = MagicMock()
    adapter = ManualHealthAdapter(session=mock_session)
    adapter._repo = AsyncMock()
    adapter._repo.get_latest_log.return_value = None

    result = await adapter.get_latest_metrics(user_id=99)
    assert result is None


@pytest.mark.asyncio
async def test_manual_adapter_get_metrics_range():
    """ManualHealthAdapter.get_metrics_range delega en HealthRepository."""
    log1 = HealthLog(
        id=1, user_id=1,
        date=date(2026, 3, 10),
        sleep_score=70.0, stress_level=5.0, hrv=50.0,
        steps=7000, mood=None, notes=None, source="manual",
        created_at=datetime(2026, 3, 10),
    )
    log2 = HealthLog(
        id=2, user_id=1,
        date=date(2026, 3, 15),
        sleep_score=80.0, stress_level=3.0, hrv=65.0,
        steps=9000, mood=None, notes=None, source="manual",
        created_at=datetime(2026, 3, 15),
    )

    mock_session = MagicMock()
    adapter = ManualHealthAdapter(session=mock_session)
    adapter._repo = AsyncMock()
    adapter._repo.get_logs.return_value = [log1, log2]

    start = date(2026, 3, 10)
    end = date(2026, 3, 19)
    results = await adapter.get_metrics_range(user_id=1, start=start, end=end)

    assert len(results) == 2
    adapter._repo.get_logs.assert_called_once_with(1, start, end)
