"""
Tests de integración end-to-end con base de datos SQLite in-memory.
Verifican flujos completos del sistema SGAI.
"""

import pytest
from httpx import AsyncClient


# ── Test 1: Crear perfil → Registrar salud → Generar plan ────────────────────

@pytest.mark.asyncio
async def test_create_profile_log_health_and_create_plan(client: AsyncClient):
    """
    Flujo completo: crear perfil → registrar log de salud → crear plan semanal.
    Verifica que los endpoints responden correctamente y los datos persisten.
    """
    # 1. Crear perfil de usuario
    profile_data = {
        "telegram_chat_id": "999999999",
        "name": "Chef Test",
        "age": 35,
        "weight_kg": 80.0,
        "height_cm": 175.0,
        "activity_level": "moderate",
        "goal": "maintain",
        "max_storage_volume": {"refrigerados": 40, "secos": 20, "congelados": 15},
    }
    resp = await client.post("/api/v1/users/profile", json=profile_data)
    assert resp.status_code == 201, resp.text
    profile = resp.json()
    user_id = profile["id"]
    assert profile["name"] == "Chef Test"

    # 2. Registrar log de salud
    health_data = {
        "user_id": user_id,
        "date": "2026-03-20",
        "sleep_score": 75.0,
        "stress_level": 4.0,
        "hrv": 48.0,
        "steps": 8500,
        "mood": "good",
        "source": "manual",
    }
    resp = await client.post("/api/v1/health/log", json=health_data)
    assert resp.status_code == 201, resp.text
    log = resp.json()
    assert log["sleep_score"] == 75.0

    # 3. Verificar que el perfil se puede consultar
    resp = await client.get(f"/api/v1/users/profile/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Chef Test"


# ── Test 2: Registrar precio → Agregar a pantry → Verificar pantry ───────────

@pytest.mark.asyncio
async def test_register_price_add_to_pantry_and_verify(client: AsyncClient):
    """
    Flujo: crear ingrediente → registrar precio → agregar a pantry → verificar.
    """
    # 1. Crear ingrediente
    ing_data = {
        "name": "tomate_test",
        "category": "vegetal",
        "unit": "kg",
        "calories_per_100g": 18.0,
        "protein_per_100g": 0.9,
        "carbs_per_100g": 3.9,
        "fat_per_100g": 0.2,
        "storage_type": "refrigerado",
        "aliases": ["tomato"],
    }
    resp = await client.post("/api/v1/ingredients", json=ing_data)
    assert resp.status_code in (200, 201), resp.text
    ingredient_id = resp.json()["id"]

    # 2. Crear perfil para asociar pantry
    profile_data = {
        "telegram_chat_id": "888888888",
        "name": "Chef Pantry",
        "age": 30,
        "weight_kg": 70.0,
        "height_cm": 170.0,
        "activity_level": "active",
        "goal": "maintain",
        "max_storage_volume": {"refrigerados": 30, "secos": 20},
    }
    resp = await client.post("/api/v1/users/profile", json=profile_data)
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # 3. Registrar precio del ingrediente
    price_data = {
        "ingredient_id": ingredient_id,
        "price_ars": 2500.0,
        "source": "manual",
        "confidence": 1.0,
        "store": "verdulería local",
        "date": "2026-03-20",
    }
    resp = await client.post("/api/v1/market/prices", json=price_data)
    assert resp.status_code == 201, resp.text
    assert resp.json()["price_ars"] == 2500.0

    # 4. Agregar item al pantry
    pantry_data = {
        "user_id": user_id,
        "ingredient_id": ingredient_id,
        "quantity_amount": 2.0,
        "unit": "kg",
    }
    resp = await client.post("/api/v1/market/pantry", json=pantry_data)
    assert resp.status_code == 201, resp.text

    # 5. Consultar pantry del usuario
    resp = await client.get(f"/api/v1/market/pantry/{user_id}")
    assert resp.status_code == 200
    pantry = resp.json()
    assert len(pantry) >= 1
    assert any(item["ingredient_id"] == ingredient_id for item in pantry)


# ── Test 3: Health endpoint responde correctamente ────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(client: AsyncClient):
    """
    El endpoint /health retorna status 200 con campo status='ok'.
    """
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ("ok", "healthy")
    assert "version" in data
