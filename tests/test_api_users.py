"""Tests de API: usuarios y preferencias."""

import pytest

VALID_PROFILE = {
    "telegram_chat_id": "6513721904",
    "name": "Felix",
    "age": 42,
    "weight_kg": 80.0,
    "height_cm": 175.0,
    "activity_level": "moderate",
    "goal": "maintain",
    "max_storage_volume": {"refrigerados": 50, "secos": 30},
}


@pytest.mark.asyncio
async def test_create_profile_returns_201(client):
    """POST con datos válidos devuelve 201 y el perfil creado."""
    resp = await client.post("/api/v1/users/profile", json=VALID_PROFILE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Felix"
    assert data["age"] == 42
    assert data["max_storage_volume"] == {"refrigerados": 50, "secos": 30}
    assert "id" in data


@pytest.mark.asyncio
async def test_create_profile_age_too_young_returns_422(client):
    """POST con age=15 falla validación Pydantic → 422."""
    payload = {**VALID_PROFILE, "age": 15}
    resp = await client.post("/api/v1/users/profile", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_profile_not_found_returns_404(client):
    """GET perfil inexistente → 404."""
    resp = await client.get("/api/v1/users/profile/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_profile(client):
    """POST luego PUT actualiza correctamente el perfil."""
    create_resp = await client.post("/api/v1/users/profile", json=VALID_PROFILE)
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/users/profile/{user_id}",
        json={"name": "Felix Updated", "weight_kg": 78.5},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Felix Updated"
    assert data["weight_kg"] == 78.5
    assert data["age"] == 42  # sin cambios


@pytest.mark.asyncio
async def test_preferences_create_and_list(client):
    """POST preferencia y luego GET lista correctamente."""
    create_resp = await client.post("/api/v1/users/profile", json=VALID_PROFILE)
    user_id = create_resp.json()["id"]

    pref_resp = await client.post(
        "/api/v1/users/preferences",
        json={"user_id": user_id, "key": "sin_gluten", "value": "true"},
    )
    assert pref_resp.status_code == 201
    assert pref_resp.json()["key"] == "sin_gluten"

    list_resp = await client.get(f"/api/v1/users/preferences/{user_id}")
    assert list_resp.status_code == 200
    prefs = list_resp.json()
    assert len(prefs) == 1
    assert prefs[0]["key"] == "sin_gluten"
