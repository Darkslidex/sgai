"""Tests del servicio de procesamiento de facturas."""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

from app.domain.models.market import MarketPrice
from app.domain.services.invoice_service import InvoiceService


def _make_ingredient(id: int, name: str, aliases: list[str] | None = None):
    ing = MagicMock()
    ing.id = id
    ing.name = name
    ing.aliases = aliases or []
    return ing


def _make_llm_response(store: str, items: list[dict]) -> dict:
    return {"store": store, "date": "2026-03-20", "items": items}


@pytest.fixture
def mock_market_repo():
    repo = MagicMock()
    repo.add_price = AsyncMock(side_effect=lambda p: p)
    return repo


@pytest.fixture
def mock_ingredient_repo():
    repo = MagicMock()
    repo.list_ingredients = AsyncMock(return_value=[
        _make_ingredient(1, "tomate", ["tomato", "tomate perita"]),
        _make_ingredient(2, "pollo", ["chicken", "pollo entero"]),
        _make_ingredient(3, "arroz", ["rice"]),
    ])
    return repo


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def invoice_service(mock_llm, mock_market_repo, mock_ingredient_repo):
    return InvoiceService(mock_llm, mock_market_repo, mock_ingredient_repo)


# ── Tests de matching ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exact_name_match(invoice_service, mock_llm, mock_market_repo):
    """Nombre exacto en la factura matchea con el ingrediente."""
    mock_llm.analyze_invoice = AsyncMock(return_value=_make_llm_response(
        "Coto", [{"name": "tomate", "price_ars": 2500.0, "quantity": 1, "unit": "kg"}]
    ))

    result = await invoice_service.process_invoice(b"fake_photo")

    assert result.total_saved == 1
    assert result.matched_items[0].ingredient_id == 1
    assert result.matched_items[0].price_ars == 2500.0
    assert result.store == "Coto"


@pytest.mark.asyncio
async def test_alias_match(invoice_service, mock_llm):
    """Alias del ingrediente matchea correctamente."""
    mock_llm.analyze_invoice = AsyncMock(return_value=_make_llm_response(
        "Carrefour", [{"name": "tomato", "price_ars": 2800.0, "quantity": 1, "unit": "kg"}]
    ))

    result = await invoice_service.process_invoice(b"fake_photo")

    assert result.total_saved == 1
    assert result.matched_items[0].ingredient_id == 1


@pytest.mark.asyncio
async def test_partial_name_match(invoice_service, mock_llm):
    """Nombre parcial (contiene el ingrediente) matchea."""
    mock_llm.analyze_invoice = AsyncMock(return_value=_make_llm_response(
        "Jumbo", [{"name": "pollo entero", "price_ars": 5000.0, "quantity": 1, "unit": "u"}]
    ))

    result = await invoice_service.process_invoice(b"fake_photo")

    assert result.total_saved == 1
    assert result.matched_items[0].ingredient_id == 2


@pytest.mark.asyncio
async def test_unmatched_items_reported(invoice_service, mock_llm):
    """Items que no matchean se reportan en unmatched_names."""
    mock_llm.analyze_invoice = AsyncMock(return_value=_make_llm_response(
        "Día", [
            {"name": "tomate", "price_ars": 2500.0, "quantity": 1, "unit": "kg"},
            {"name": "producto_desconocido_xyz", "price_ars": 999.0, "quantity": 1, "unit": "u"},
        ]
    ))

    result = await invoice_service.process_invoice(b"fake_photo")

    assert result.total_saved == 1
    assert "producto_desconocido_xyz" in result.unmatched_names


@pytest.mark.asyncio
async def test_price_saved_with_factura_source(invoice_service, mock_llm, mock_market_repo):
    """El precio guardado tiene source='factura' y confidence=1.0."""
    mock_llm.analyze_invoice = AsyncMock(return_value=_make_llm_response(
        "Disco", [{"name": "arroz", "price_ars": 1800.0, "quantity": 1, "unit": "kg"}]
    ))

    await invoice_service.process_invoice(b"fake_photo")

    saved: MarketPrice = mock_market_repo.add_price.call_args[0][0]
    assert saved.source == "factura"
    assert saved.confidence == 1.0
    assert saved.store == "Disco"
    assert saved.price_ars == 1800.0


@pytest.mark.asyncio
async def test_empty_items_returns_zero_saved(invoice_service, mock_llm):
    """Si LLM no extrae items, retorna 0 guardados."""
    mock_llm.analyze_invoice = AsyncMock(return_value=_make_llm_response("Coto", []))

    result = await invoice_service.process_invoice(b"fake_photo")

    assert result.total_saved == 0
    assert result.matched_items == []


@pytest.mark.asyncio
async def test_items_with_zero_price_skipped(invoice_service, mock_llm):
    """Items con precio 0 o negativo se ignoran."""
    mock_llm.analyze_invoice = AsyncMock(return_value=_make_llm_response(
        "Coto", [{"name": "tomate", "price_ars": 0, "quantity": 1, "unit": "kg"}]
    ))

    result = await invoice_service.process_invoice(b"fake_photo")

    assert result.total_saved == 0
