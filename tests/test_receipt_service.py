"""Tests del ReceiptService — fuzzy matching y registro de precios."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.services.receipt_service import ReceiptService


def _make_ingredient(id: int, name: str, aliases: list[str] | None = None):
    ing = MagicMock()
    ing.id = id
    ing.name = name
    ing.aliases = aliases or []
    return ing


@pytest.fixture
def mock_market_repo():
    repo = MagicMock()
    repo.add_price = AsyncMock(side_effect=lambda p: p)
    return repo


@pytest.fixture
def mock_ingredient_repo():
    ingredients = [
        _make_ingredient(1, "pollo", ["chicken", "pollo entero", "pechuga"]),
        _make_ingredient(2, "tomate", ["tomato", "tomate perita"]),
        _make_ingredient(3, "arroz", ["rice", "arroz largo fino"]),
    ]
    repo = MagicMock()
    repo.list_ingredients = AsyncMock(return_value=ingredients)
    # search_ingredients_fuzzy devuelve lista vacía por defecto (sin pg_trgm en tests)
    repo.search_ingredients_fuzzy = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def service(mock_ingredient_repo, mock_market_repo):
    return ReceiptService(mock_ingredient_repo, mock_market_repo)


@pytest.mark.asyncio
async def test_exact_name_match(service, mock_market_repo):
    """Nombre exacto matchea y registra el precio."""
    result = await service.process_items(
        store_name="Coto",
        purchase_date=date.today(),
        items=[{"product_name": "pollo", "price_ars": 3500.0}],
    )
    assert result.registered == 1
    assert result.skipped == 0
    assert mock_market_repo.add_price.called


@pytest.mark.asyncio
async def test_alias_match(service):
    """Alias del ingrediente matchea (ej. 'chicken' → 'pollo')."""
    result = await service.process_items(
        store_name="Jumbo",
        purchase_date=date.today(),
        items=[{"product_name": "chicken breast", "price_ars": 4000.0}],
    )
    assert result.registered == 1
    assert result.detail[0].matched_ingredient_name == "pollo"


@pytest.mark.asyncio
async def test_contains_match(service):
    """Nombre parcial matchea (ej. 'arroz largo fino' → 'arroz')."""
    result = await service.process_items(
        store_name="Carrefour",
        purchase_date=date.today(),
        items=[{"product_name": "arroz largo fino x1kg", "price_ars": 1200.0}],
    )
    assert result.registered == 1
    assert result.detail[0].matched_ingredient_name == "arroz"


@pytest.mark.asyncio
async def test_unmatched_reported_in_skipped(service):
    """Producto sin match → aparece en skipped_items."""
    result = await service.process_items(
        store_name="Día",
        purchase_date=date.today(),
        items=[{"product_name": "detergente xyz marca desconocida", "price_ars": 500.0}],
    )
    assert result.registered == 0
    assert result.skipped == 1
    assert "detergente xyz marca desconocida" in result.skipped_items


@pytest.mark.asyncio
async def test_mixed_items(service, mock_market_repo):
    """Mezcla de ítems conocidos y desconocidos."""
    result = await service.process_items(
        store_name="Coto",
        purchase_date=date.today(),
        items=[
            {"product_name": "tomate perita", "price_ars": 2000.0},
            {"product_name": "zapatillas_producto_inexistente", "price_ars": 999.0},
            {"product_name": "arroz", "price_ars": 1500.0},
        ],
    )
    assert result.registered == 2
    assert result.skipped == 1
    assert mock_market_repo.add_price.call_count == 2


@pytest.mark.asyncio
async def test_price_saved_with_correct_source_and_store(service, mock_market_repo):
    """El precio guardado tiene source='receipt', confidence=1.0 y store correcto."""
    await service.process_items(
        store_name="Disco",
        purchase_date=date.today(),
        items=[{"product_name": "pollo", "price_ars": 3800.0}],
    )
    saved = mock_market_repo.add_price.call_args[0][0]
    assert saved.source == "receipt"
    assert saved.confidence == 1.0
    assert saved.store == "Disco"
    assert saved.price_ars == 3800.0


@pytest.mark.asyncio
async def test_zero_price_items_skipped(service, mock_market_repo):
    """Ítems con precio 0 se ignoran sin error."""
    result = await service.process_items(
        store_name="Coto",
        purchase_date=date.today(),
        items=[{"product_name": "pollo", "price_ars": 0}],
    )
    assert result.registered == 0
    assert not mock_market_repo.add_price.called


@pytest.mark.asyncio
async def test_fuzzy_match_used_when_available(mock_ingredient_repo, mock_market_repo):
    """Si search_ingredients_fuzzy devuelve resultado, se usa sin ir al fallback Python."""
    pollo = _make_ingredient(1, "pollo")
    mock_ingredient_repo.search_ingredients_fuzzy = AsyncMock(return_value=[pollo])

    service = ReceiptService(mock_ingredient_repo, mock_market_repo)
    result = await service.process_items(
        store_name="Coto",
        purchase_date=date.today(),
        items=[{"product_name": "pechuga de pollo sin hueso", "price_ars": 4200.0}],
    )
    assert result.registered == 1
    # No debería haber llamado a list_ingredients (fallback Python no fue necesario)
    mock_ingredient_repo.list_ingredients.assert_not_called()
