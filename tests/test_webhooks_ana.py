"""Tests de los endpoints webhook Ana → SGAI.

Cubre autenticación, health-log, receipt, price-check y biometrics.
Usa SQLite in-memory + fixture client del conftest.
"""

from datetime import date

import pytest

ANA_KEY = "test-ana-key-for-testing-only"
AUTH_HEADER = {"X-Ana-Key": ANA_KEY}

VALID_USER = {
    "telegram_chat_id": "123456789",
    "name": "Felix",
    "age": 42,
    "weight_kg": 80.0,
    "height_cm": 175.0,
    "activity_level": "moderate",
    "goal": "maintain",
}

VALID_INGREDIENT = {
    "name": "pollo",
    "aliases": ["chicken", "pollo entero"],
    "category": "proteina",
    "storage_type": "refrigerado",
    "unit": "kg",
    "protein_per_100g": 31.0,
    "calories_per_100g": 165.0,
    "avg_shelf_life_days": 5,
}


# ── Autenticación ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_rejects_missing_key(client):
    """Sin header X-Ana-Key → 403."""
    resp = await client.post(
        "/api/v1/webhooks/ana/health-log",
        json={"user_id": 1, "date": str(date.today())},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_key(client):
    """Header X-Ana-Key incorrecto → 401."""
    resp = await client.post(
        "/api/v1/webhooks/ana/health-log",
        headers={"X-Ana-Key": "wrong-key"},
        json={"user_id": 1, "date": str(date.today())},
    )
    assert resp.status_code == 401


# ── Health Log ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_log_creates_record(client):
    """Ana envía health log con sleep_hours → se guarda con sleep_score correcto."""
    user_resp = await client.post("/api/v1/users/profile", json=VALID_USER)
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]

    resp = await client.post(
        "/api/v1/webhooks/ana/health-log",
        headers=AUTH_HEADER,
        json={
            "user_id": user_id,
            "date": str(date.today()),
            "sleep_hours": 7.5,
            "steps": 9000,
            "hrv": 50.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ok"] is True
    assert data["health_log_id"] > 0
    # sleep_score = min(7.5 / 9 * 100, 100) ≈ 83.3
    assert data["sleep_score"] == pytest.approx(83.3, abs=0.2)


@pytest.mark.asyncio
async def test_health_log_sleep_hours_max_capped(client):
    """sleep_hours = 9 → sleep_score = 100 (no supera el techo)."""
    user_resp = await client.post("/api/v1/users/profile", json=VALID_USER)
    user_id = user_resp.json()["id"]

    resp = await client.post(
        "/api/v1/webhooks/ana/health-log",
        headers=AUTH_HEADER,
        json={"user_id": user_id, "date": str(date.today()), "sleep_hours": 10.0},
    )
    assert resp.status_code == 201
    assert resp.json()["sleep_score"] == 100.0


@pytest.mark.asyncio
async def test_health_log_without_sleep_hours(client):
    """Sin sleep_hours → sleep_score None."""
    user_resp = await client.post("/api/v1/users/profile", json=VALID_USER)
    user_id = user_resp.json()["id"]

    resp = await client.post(
        "/api/v1/webhooks/ana/health-log",
        headers=AUTH_HEADER,
        json={"user_id": user_id, "date": str(date.today()), "steps": 5000},
    )
    assert resp.status_code == 201
    assert resp.json()["sleep_score"] is None


# ── Receipt ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_receipt_registers_known_ingredient(client):
    """Ana envía ticket con producto conocido → se registra el precio."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    assert ing_resp.status_code == 201

    resp = await client.post(
        "/api/v1/webhooks/ana/receipt",
        headers=AUTH_HEADER,
        json={
            "store_name": "Coto",
            "purchase_date": str(date.today()),
            "items": [{"product_name": "pollo", "price_ars": 3500.0, "quantity": 1}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ok"] is True
    assert data["registered"] == 1
    assert data["skipped"] == 0


@pytest.mark.asyncio
async def test_receipt_reports_unknown_ingredient(client):
    """Producto sin match en la DB → se reporta en skipped_items."""
    resp = await client.post(
        "/api/v1/webhooks/ana/receipt",
        headers=AUTH_HEADER,
        json={
            "store_name": "Jumbo",
            "purchase_date": str(date.today()),
            "items": [{"product_name": "producto_desconocido_xyz_999", "price_ars": 1000.0}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["registered"] == 0
    assert data["skipped"] == 1
    assert "producto_desconocido_xyz_999" in data["skipped_items"]


@pytest.mark.asyncio
async def test_receipt_requires_at_least_one_item(client):
    """Lista de items vacía → 422."""
    resp = await client.post(
        "/api/v1/webhooks/ana/receipt",
        headers=AUTH_HEADER,
        json={"store_name": "Coto", "purchase_date": str(date.today()), "items": []},
    )
    assert resp.status_code == 422


# ── Price Check ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_price_check_no_history_returns_sin_historial(client):
    """Sin historial previo → veredicto sin_historial."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    assert ing_resp.status_code == 201

    resp = await client.post(
        "/api/v1/webhooks/ana/price-check",
        headers=AUTH_HEADER,
        json={"ingredient_name": "pollo", "price_ars": 3000.0, "store": "Coto"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "sin_historial"


@pytest.mark.asyncio
async def test_price_check_conveniente(client):
    """Precio por debajo del promedio → veredicto conveniente."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    ing_id = ing_resp.json()["id"]

    # Cargar historial: promedio 4000
    for price in [3500.0, 4000.0, 4500.0]:
        await client.post(
            "/api/v1/market/prices",
            json={
                "ingredient_id": ing_id,
                "price_ars": price,
                "source": "manual",
                "date": str(date.today()),
            },
        )

    resp = await client.post(
        "/api/v1/webhooks/ana/price-check",
        headers=AUTH_HEADER,
        json={"ingredient_name": "pollo", "price_ars": 3200.0},
    )
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "conveniente"


@pytest.mark.asyncio
async def test_price_check_muy_caro(client):
    """Precio por encima del máximo histórico → veredicto muy_caro."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    ing_id = ing_resp.json()["id"]

    await client.post(
        "/api/v1/market/prices",
        json={
            "ingredient_id": ing_id,
            "price_ars": 4000.0,
            "source": "manual",
            "date": str(date.today()),
        },
    )

    resp = await client.post(
        "/api/v1/webhooks/ana/price-check",
        headers=AUTH_HEADER,
        json={"ingredient_name": "pollo", "price_ars": 9999.0},
    )
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "muy_caro"


@pytest.mark.asyncio
async def test_price_check_unknown_ingredient_returns_404(client):
    """Ingrediente no encontrado → 404."""
    resp = await client.post(
        "/api/v1/webhooks/ana/price-check",
        headers=AUTH_HEADER,
        json={"ingredient_name": "producto_inexistente_xyz", "price_ars": 100.0},
    )
    assert resp.status_code == 404


# ── Biometrics ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_biometrics_creates_health_log(client):
    """Ana envía biometría de Google Fit → log de salud creado."""
    user_resp = await client.post("/api/v1/users/profile", json=VALID_USER)
    user_id = user_resp.json()["id"]

    resp = await client.post(
        "/api/v1/webhooks/ana/biometrics",
        headers=AUTH_HEADER,
        json={
            "user_id": user_id,
            "date": str(date.today()),
            "sleep_hours": 8.0,
            "deep_sleep_minutes": 90,
            "steps": 10000,
            "heart_rate_avg": 68.0,
            "hrv": 52.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ok"] is True
    assert data["health_log_id"] > 0
    # sleep_score = 8/9*100 ≈ 88.9
    assert data["sleep_score"] == pytest.approx(88.9, abs=0.2)


@pytest.mark.asyncio
async def test_biometrics_returns_tdee_when_profile_exists(client):
    """Biometría con perfil de usuario → respuesta incluye tdee_kcal."""
    user_resp = await client.post("/api/v1/users/profile", json=VALID_USER)
    user_id = user_resp.json()["id"]

    resp = await client.post(
        "/api/v1/webhooks/ana/biometrics",
        headers=AUTH_HEADER,
        json={
            "user_id": user_id,
            "date": str(date.today()),
            "sleep_hours": 7.0,
            "steps": 8000,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tdee_kcal"] is not None
    assert data["tdee_kcal"] > 1000


@pytest.mark.asyncio
async def test_biometrics_partial_data(client):
    """Biometría con solo steps → se acepta sin error."""
    user_resp = await client.post("/api/v1/users/profile", json=VALID_USER)
    user_id = user_resp.json()["id"]

    resp = await client.post(
        "/api/v1/webhooks/ana/biometrics",
        headers=AUTH_HEADER,
        json={"user_id": user_id, "date": str(date.today()), "steps": 6000},
    )
    assert resp.status_code == 201
    assert resp.json()["ok"] is True
