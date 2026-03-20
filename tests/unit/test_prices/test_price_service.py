"""Tests del servicio de precios híbrido (3 niveles) y circuit breaker."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.domain.models.market import MarketPrice
from app.domain.services.price_service import PriceService
from app.adapters.pricing.scraping_price_adapter import ScrapingPriceAdapter


def _make_price(ingredient_id=1, price_ars=1000.0, source="manual", days_ago=0, confidence=1.0):
    return MarketPrice(
        id=1,
        ingredient_id=ingredient_id,
        price_ars=price_ars,
        source=source,
        store="Coto",
        confidence=confidence,
        date=date.today() - timedelta(days=days_ago),
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_market_repo():
    repo = MagicMock()
    repo.get_current_price = AsyncMock(return_value=None)
    repo.get_price_history = AsyncMock(return_value=[])
    repo.add_price = AsyncMock(side_effect=lambda p: p)
    return repo


@pytest.fixture
def mock_manual_adapter():
    adapter = MagicMock()
    adapter.get_price = AsyncMock(return_value=None)
    adapter.save_price = AsyncMock()
    return adapter


@pytest.fixture
def mock_sepa_adapter():
    adapter = MagicMock()
    adapter.get_price = AsyncMock(return_value=None)
    adapter.save_price = AsyncMock()
    return adapter


@pytest.fixture
def mock_scraping_adapter():
    adapter = MagicMock()
    adapter.get_price = AsyncMock(return_value=None)
    adapter.save_price = AsyncMock()
    return adapter


@pytest.fixture
def price_service(mock_manual_adapter, mock_sepa_adapter, mock_scraping_adapter, mock_market_repo):
    return PriceService(
        manual_adapter=mock_manual_adapter,
        sepa_adapter=mock_sepa_adapter,
        scraping_adapter=mock_scraping_adapter,
        market_repo=mock_market_repo,
    )


# ── Tests de prioridad ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manual_price_has_highest_priority(price_service, mock_manual_adapter, mock_sepa_adapter, mock_scraping_adapter):
    """Precio manual (reciente) debe retornarse sin consultar SEPA ni scraping."""
    manual_price = _make_price(source="manual", price_ars=1500.0)
    mock_manual_adapter.get_price.return_value = manual_price

    result = await price_service.get_best_price(ingredient_id=1)

    assert result is manual_price
    mock_sepa_adapter.get_price.assert_not_called()
    mock_scraping_adapter.get_price.assert_not_called()


@pytest.mark.asyncio
async def test_sepa_used_when_no_manual_price(price_service, mock_manual_adapter, mock_sepa_adapter, mock_scraping_adapter):
    """Si no hay precio manual reciente, debe usarse SEPA."""
    sepa_price = _make_price(source="sepa", price_ars=1200.0, confidence=0.8)
    mock_manual_adapter.get_price.return_value = None
    mock_sepa_adapter.get_price.return_value = sepa_price

    result = await price_service.get_best_price(ingredient_id=1)

    assert result is sepa_price
    mock_scraping_adapter.get_price.assert_not_called()


@pytest.mark.asyncio
async def test_scraping_used_when_sepa_unavailable(price_service, mock_manual_adapter, mock_sepa_adapter, mock_scraping_adapter):
    """Si SEPA no responde, debe usarse scraping."""
    scraping_price = _make_price(source="scraping", price_ars=1100.0, confidence=0.6)
    mock_manual_adapter.get_price.return_value = None
    mock_sepa_adapter.get_price.return_value = None
    mock_scraping_adapter.get_price.return_value = scraping_price

    result = await price_service.get_best_price(ingredient_id=1)

    assert result is scraping_price


@pytest.mark.asyncio
async def test_fallback_to_last_known_price(price_service, mock_manual_adapter, mock_sepa_adapter, mock_scraping_adapter, mock_market_repo):
    """Si ninguna fuente responde, retorna el último precio conocido en DB."""
    last_price = _make_price(source="manual", price_ars=900.0, days_ago=15)
    mock_manual_adapter.get_price.return_value = None
    mock_sepa_adapter.get_price.return_value = None
    mock_scraping_adapter.get_price.return_value = None
    mock_market_repo.get_current_price.return_value = last_price

    result = await price_service.get_best_price(ingredient_id=1)

    assert result is last_price
    mock_market_repo.get_current_price.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_stale_manual_price_triggers_fallback_to_sepa(price_service, mock_manual_adapter, mock_sepa_adapter):
    """Precio manual con más de 7 días de antigüedad no es válido → usar SEPA."""
    stale_manual = _make_price(source="manual", price_ars=1500.0, days_ago=10)
    sepa_price = _make_price(source="sepa", price_ars=1600.0, confidence=0.8)
    mock_manual_adapter.get_price.return_value = stale_manual
    mock_sepa_adapter.get_price.return_value = sepa_price

    result = await price_service.get_best_price(ingredient_id=1)

    assert result is sepa_price


# ── Tests de degradación graceful (SEPA timeout) ──────────────────────────────

@pytest.mark.asyncio
async def test_sepa_timeout_returns_none_gracefully(mock_market_repo):
    """SEPAPriceAdapter retorna None en timeout sin propagar excepción."""
    import httpx
    from unittest.mock import patch, AsyncMock as AM

    from app.adapters.pricing.sepa_price_adapter import SEPAPriceAdapter

    repo = mock_market_repo
    adapter = SEPAPriceAdapter(repo, ingredient_names={1: "tomate"})

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client_class.return_value = mock_client

        result = await adapter.get_price(1)

    assert result is None


@pytest.mark.asyncio
async def test_sepa_http_error_returns_none_gracefully(mock_market_repo):
    """SEPAPriceAdapter retorna None en HTTP error sin propagar excepción."""
    import httpx
    from unittest.mock import patch, AsyncMock as AM

    from app.adapters.pricing.sepa_price_adapter import SEPAPriceAdapter

    adapter = SEPAPriceAdapter(mock_market_repo, ingredient_names={1: "arroz"})

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("error"))
        mock_client_class.return_value = mock_client

        result = await adapter.get_price(1)

    assert result is None


# ── Tests del circuit breaker de scraping ────────────────────────────────────

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_max_failures(mock_market_repo):
    """Después de MAX_FAILURES fallos, el circuit breaker se activa."""
    adapter = ScrapingPriceAdapter(mock_market_repo)
    adapter.register_ingredient(1, "pollo")

    assert adapter._is_circuit_open() is False

    for _ in range(adapter.MAX_FAILURES):
        adapter._record_failure()

    assert adapter._is_circuit_open() is True


@pytest.mark.asyncio
async def test_circuit_breaker_open_returns_none(mock_market_repo):
    """Con el circuit abierto, get_price retorna None sin intentar scraping."""
    adapter = ScrapingPriceAdapter(mock_market_repo)
    adapter.register_ingredient(1, "pollo")

    # Activar circuit breaker manualmente
    for _ in range(adapter.MAX_FAILURES):
        adapter._record_failure()

    result = await adapter.get_price(1)
    assert result is None


@pytest.mark.asyncio
async def test_circuit_breaker_resets_after_cooldown(mock_market_repo):
    """Después del período de cooldown, el circuit breaker se resetea."""
    from datetime import datetime, timedelta

    adapter = ScrapingPriceAdapter(mock_market_repo)

    # Activar circuit breaker con fecha ya expirada
    for _ in range(adapter.MAX_FAILURES):
        adapter._record_failure()

    # Simular que el cooldown ya pasó
    adapter.circuit_open_until = datetime.now() - timedelta(seconds=1)

    assert adapter._is_circuit_open() is False
    assert adapter.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_success_resets_failure_count(mock_market_repo):
    """Un éxito resetea el contador de fallos."""
    adapter = ScrapingPriceAdapter(mock_market_repo)

    adapter.failure_count = 2
    adapter._record_success()

    assert adapter.failure_count == 0


# ── Tests de detección de anomalías ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_price_anomaly_detected_on_high_jump(price_service, mock_market_repo):
    """Detecta anomalía cuando precio sube >50% sobre el promedio histórico."""
    history = [_make_price(price_ars=1000.0, days_ago=i) for i in range(5)]
    mock_market_repo.get_price_history.return_value = history

    is_anomaly = await price_service.detect_price_anomaly(ingredient_id=1, new_price=2000.0)

    assert is_anomaly is True


@pytest.mark.asyncio
async def test_price_anomaly_detected_on_low_drop(price_service, mock_market_repo):
    """Detecta anomalía cuando precio baja >70% (posible error de tipeo)."""
    history = [_make_price(price_ars=1000.0, days_ago=i) for i in range(5)]
    mock_market_repo.get_price_history.return_value = history

    is_anomaly = await price_service.detect_price_anomaly(ingredient_id=1, new_price=200.0)

    assert is_anomaly is True


@pytest.mark.asyncio
async def test_normal_price_no_anomaly(price_service, mock_market_repo):
    """Precio dentro del rango normal no genera anomalía."""
    history = [_make_price(price_ars=1000.0, days_ago=i) for i in range(5)]
    mock_market_repo.get_price_history.return_value = history

    is_anomaly = await price_service.detect_price_anomaly(ingredient_id=1, new_price=1200.0)

    assert is_anomaly is False


@pytest.mark.asyncio
async def test_no_anomaly_without_enough_history(price_service, mock_market_repo):
    """Sin historial suficiente (< 3 registros), no se detectan anomalías."""
    mock_market_repo.get_price_history.return_value = [_make_price(price_ars=1000.0)]

    is_anomaly = await price_service.detect_price_anomaly(ingredient_id=1, new_price=9999.0)

    assert is_anomaly is False
