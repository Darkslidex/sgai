"""Tests de API: precios de mercado y despensa."""

from datetime import date

import pytest

VALID_INGREDIENT = {
    "name": "Arroz Largo Fino",
    "aliases": [],
    "category": "carbohidrato",
    "storage_type": "seco",
    "unit": "kg",
    "protein_per_100g": 7.0,
    "calories_per_100g": 365.0,
    "avg_shelf_life_days": 365,
}


@pytest.mark.asyncio
async def test_add_price_zero_returns_422(client):
    """POST precio con price_ars=0 → 422 (violación gt=0)."""
    resp = await client.post(
        "/api/v1/market/prices",
        json={
            "ingredient_id": 1,
            "price_ars": 0,
            "source": "manual",
            "date": str(date.today()),
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_price_valid_returns_201(client):
    """POST precio válido → 201 con los datos persistidos."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    assert ing_resp.status_code == 201
    ing_id = ing_resp.json()["id"]

    resp = await client.post(
        "/api/v1/market/prices",
        json={
            "ingredient_id": ing_id,
            "price_ars": 850.0,
            "source": "manual",
            "store": "Coto",
            "confidence": 0.9,
            "date": str(date.today()),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["price_ars"] == 850.0
    assert data["store"] == "Coto"


@pytest.mark.asyncio
async def test_get_current_prices_returns_latest(client):
    """GET /market/prices/current retorna el precio más reciente por ingrediente."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    ing_id = ing_resp.json()["id"]

    today = str(date.today())
    await client.post(
        "/api/v1/market/prices",
        json={"ingredient_id": ing_id, "price_ars": 800.0, "source": "manual", "date": today},
    )

    resp = await client.get("/api/v1/market/prices/current")
    assert resp.status_code == 200
    prices = resp.json()
    ingredient_prices = [p for p in prices if p["ingredient_id"] == ing_id]
    assert len(ingredient_prices) == 1
    assert ingredient_prices[0]["price_ars"] == 800.0


@pytest.mark.asyncio
async def test_pantry_add_and_get(client):
    """POST pantry item y GET lista correctamente."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    ing_id = ing_resp.json()["id"]

    post_resp = await client.post(
        "/api/v1/market/pantry",
        json={
            "user_id": 1,
            "ingredient_id": ing_id,
            "quantity_amount": 2.0,
            "unit": "kg",
        },
    )
    assert post_resp.status_code == 201
    assert post_resp.json()["quantity_amount"] == 2.0

    get_resp = await client.get("/api/v1/market/pantry/1")
    assert get_resp.status_code == 200
    items = get_resp.json()
    matching = [i for i in items if i["ingredient_id"] == ing_id]
    assert len(matching) == 1
