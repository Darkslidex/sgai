"""Tests de API: recetas."""

import pytest

VALID_INGREDIENT = {
    "name": "Pechuga de Pollo",
    "aliases": ["pollo"],
    "category": "proteina",
    "storage_type": "refrigerado",
    "unit": "kg",
    "protein_per_100g": 23.0,
    "calories_per_100g": 165.0,
    "avg_shelf_life_days": 3,
}


def make_recipe(ingredient_id: int, batch: bool = True) -> dict:
    return {
        "name": "Arroz con pollo",
        "description": "Clásico argentino ideal para batch cooking",
        "prep_time_minutes": 30,
        "is_batch_friendly": batch,
        "reheatable_days": 4,
        "servings": 5,
        "calories_per_serving": 450.0,
        "protein_per_serving": 35.0,
        "carbs_per_serving": 50.0,
        "fat_per_serving": 10.0,
        "instructions": '[{"paso": 1, "texto": "Cocinar arroz"}]',
        "tags": ["alta_proteina", "batch_cooking"],
        "ingredients": [
            {"ingredient_id": ingredient_id, "quantity_amount": 0.5, "unit": "kg"}
        ],
    }


@pytest.mark.asyncio
async def test_create_recipe_returns_201(client):
    """POST receta con ingredientes → 201."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    assert ing_resp.status_code == 201
    ing_id = ing_resp.json()["id"]

    recipe_resp = await client.post("/api/v1/recipes", json=make_recipe(ing_id))
    assert recipe_resp.status_code == 201
    data = recipe_resp.json()
    assert data["name"] == "Arroz con pollo"
    assert data["is_batch_friendly"] is True
    assert data["reheatable_days"] == 4


@pytest.mark.asyncio
async def test_list_recipes_returns_all(client):
    """GET /recipes lista todas las recetas creadas."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    ing_id = ing_resp.json()["id"]

    await client.post("/api/v1/recipes", json=make_recipe(ing_id))
    await client.post("/api/v1/recipes", json={**make_recipe(ing_id), "name": "Milanesa"})

    list_resp = await client.get("/api/v1/recipes")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 2


@pytest.mark.asyncio
async def test_list_recipes_filter_batch(client):
    """GET /recipes?is_batch_friendly=true filtra correctamente."""
    ing_resp = await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)
    ing_id = ing_resp.json()["id"]

    await client.post("/api/v1/recipes", json=make_recipe(ing_id, batch=True))
    await client.post("/api/v1/recipes", json={**make_recipe(ing_id, batch=False), "name": "Simple"})

    resp = await client.get("/api/v1/recipes?is_batch_friendly=true")
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["is_batch_friendly"] for r in results)


@pytest.mark.asyncio
async def test_overlapping_recipes(client):
    """GET /recipes/overlapping retorna recetas con solapamiento de ingredientes."""
    ing1 = (await client.post("/api/v1/ingredients", json=VALID_INGREDIENT)).json()["id"]
    ing2 = (await client.post("/api/v1/ingredients", json={
        **VALID_INGREDIENT, "name": "Arroz"
    })).json()["id"]

    # Receta que usa ambos ingredientes
    recipe_payload = make_recipe(ing1)
    recipe_payload["ingredients"].append({"ingredient_id": ing2, "quantity_amount": 0.3, "unit": "kg"})
    await client.post("/api/v1/recipes", json=recipe_payload)

    resp = await client.get(f"/api/v1/recipes/overlapping?ingredient_ids={ing1},{ing2}&min_overlap=2")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
