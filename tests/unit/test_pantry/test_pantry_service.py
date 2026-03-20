"""Tests del PantryService: CRUD de alacena y control de vencimientos."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.domain.models.ingredient import Ingredient
from app.domain.models.pantry_item import PantryItem
from app.domain.services.pantry_service import PantryService


def _make_ingredient(id=1, name="arroz", unit="kg"):
    return Ingredient(
        id=id,
        name=name,
        aliases=[],
        category="carbohidrato",
        storage_type="seco",
        unit=unit,
        protein_per_100g=2.6,
        calories_per_100g=350.0,
        avg_shelf_life_days=365,
        created_at=datetime.utcnow(),
    )


def _make_pantry_item(id=1, user_id=1, ingredient_id=1, quantity=2.0, unit="kg", expires_at=None):
    return PantryItem(
        id=id,
        user_id=user_id,
        ingredient_id=ingredient_id,
        quantity_amount=quantity,
        unit=unit,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_market_repo():
    repo = MagicMock()
    repo.get_pantry_item = AsyncMock(return_value=None)
    repo.update_pantry = AsyncMock(side_effect=lambda item: item)
    repo.delete_pantry_item = AsyncMock(return_value=None)
    repo.get_expiring_pantry = AsyncMock(return_value=[])
    repo.get_expired_pantry = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_ingredient_repo():
    repo = MagicMock()
    repo.get_ingredient = AsyncMock(return_value=_make_ingredient())
    return repo


@pytest.fixture
def pantry_service(mock_market_repo, mock_ingredient_repo):
    return PantryService(mock_market_repo, mock_ingredient_repo)


# ── add_item ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_item_creates_new_when_not_exists(pantry_service, mock_market_repo, mock_ingredient_repo):
    """add_item crea un nuevo item cuando no existe en el pantry."""
    mock_market_repo.get_pantry_item.return_value = None
    mock_ingredient_repo.get_ingredient.return_value = _make_ingredient(id=1, unit="kg")

    result = await pantry_service.add_item(user_id=1, ingredient_id=1, quantity=2.0)

    assert result.quantity_amount == 2.0
    assert result.unit == "kg"
    assert result.user_id == 1
    mock_market_repo.update_pantry.assert_called_once()


@pytest.mark.asyncio
async def test_add_item_accumulates_existing_quantity(pantry_service, mock_market_repo):
    """add_item suma la cantidad si el item ya existe."""
    existing = _make_pantry_item(quantity=3.0, unit="kg")
    mock_market_repo.get_pantry_item.return_value = existing

    result = await pantry_service.add_item(user_id=1, ingredient_id=1, quantity=1.5)

    assert result.quantity_amount == 4.5  # 3.0 + 1.5


@pytest.mark.asyncio
async def test_add_item_updates_expiry_when_provided(pantry_service, mock_market_repo):
    """add_item actualiza la fecha de vencimiento si se provee."""
    existing = _make_pantry_item(quantity=1.0, expires_at=None)
    mock_market_repo.get_pantry_item.return_value = existing
    new_expiry = date.today() + timedelta(days=7)

    result = await pantry_service.add_item(user_id=1, ingredient_id=1, quantity=0.5, expiry_date=new_expiry)

    assert result.expires_at is not None


@pytest.mark.asyncio
async def test_add_item_raises_on_nonexistent_ingredient(pantry_service, mock_market_repo, mock_ingredient_repo):
    """add_item lanza ValueError si el ingrediente no existe."""
    mock_market_repo.get_pantry_item.return_value = None
    mock_ingredient_repo.get_ingredient.return_value = None

    with pytest.raises(ValueError, match="no encontrado"):
        await pantry_service.add_item(user_id=1, ingredient_id=999, quantity=1.0)


@pytest.mark.asyncio
async def test_add_item_raises_on_zero_quantity(pantry_service):
    """add_item lanza ValueError si la cantidad es 0 o negativa."""
    with pytest.raises(ValueError):
        await pantry_service.add_item(user_id=1, ingredient_id=1, quantity=0.0)


# ── remove_item ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_remove_item_reduces_quantity(pantry_service, mock_market_repo):
    """remove_item reduce la cantidad existente."""
    existing = _make_pantry_item(quantity=5.0)
    mock_market_repo.get_pantry_item.return_value = existing

    result = await pantry_service.remove_item(user_id=1, ingredient_id=1, quantity=2.0)

    assert result is not None
    assert result.quantity_amount == 3.0


@pytest.mark.asyncio
async def test_remove_item_deletes_when_quantity_reaches_zero(pantry_service, mock_market_repo):
    """remove_item elimina el item cuando la cantidad llega a 0."""
    existing = _make_pantry_item(quantity=2.0)
    mock_market_repo.get_pantry_item.return_value = existing

    result = await pantry_service.remove_item(user_id=1, ingredient_id=1, quantity=2.0)

    assert result is None
    mock_market_repo.delete_pantry_item.assert_called_once_with(1, 1)


@pytest.mark.asyncio
async def test_remove_item_deletes_when_quantity_exceeds_stock(pantry_service, mock_market_repo):
    """remove_item elimina el item si la cantidad a remover excede el stock."""
    existing = _make_pantry_item(quantity=1.0)
    mock_market_repo.get_pantry_item.return_value = existing

    result = await pantry_service.remove_item(user_id=1, ingredient_id=1, quantity=5.0)

    assert result is None
    mock_market_repo.delete_pantry_item.assert_called_once()


@pytest.mark.asyncio
async def test_remove_item_returns_none_if_not_in_pantry(pantry_service, mock_market_repo):
    """remove_item retorna None si el ingrediente no está en el pantry."""
    mock_market_repo.get_pantry_item.return_value = None

    result = await pantry_service.remove_item(user_id=1, ingredient_id=99, quantity=1.0)

    assert result is None


# ── get_expiring_soon ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_expiring_soon_returns_items_within_days(pantry_service, mock_market_repo):
    """get_expiring_soon retorna items correctos según la ventana de días."""
    expiring_item = _make_pantry_item(expires_at=datetime.utcnow() + timedelta(days=2))
    mock_market_repo.get_expiring_pantry.return_value = [expiring_item]

    result = await pantry_service.get_expiring_soon(user_id=1, days=3)

    assert len(result) == 1
    assert result[0] is expiring_item
    mock_market_repo.get_expiring_pantry.assert_called_once_with(1, days=3)


@pytest.mark.asyncio
async def test_get_expiring_soon_returns_empty_when_none(pantry_service, mock_market_repo):
    """get_expiring_soon retorna lista vacía si no hay items próximos a vencer."""
    mock_market_repo.get_expiring_pantry.return_value = []

    result = await pantry_service.get_expiring_soon(user_id=1, days=3)

    assert result == []


# ── get_expired ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_expired_returns_expired_items(pantry_service, mock_market_repo):
    """get_expired retorna items ya vencidos."""
    expired_item = _make_pantry_item(expires_at=datetime.utcnow() - timedelta(days=1))
    mock_market_repo.get_expired_pantry.return_value = [expired_item]

    result = await pantry_service.get_expired(user_id=1)

    assert len(result) == 1
    assert result[0] is expired_item


@pytest.mark.asyncio
async def test_get_expired_empty_when_all_fresh(pantry_service, mock_market_repo):
    """get_expired retorna lista vacía si no hay items vencidos."""
    mock_market_repo.get_expired_pantry.return_value = []

    result = await pantry_service.get_expired(user_id=1)

    assert result == []
