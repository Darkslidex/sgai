"""Endpoints CRUD para ingredientes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.ingredient_repo import IngredientRepository
from app.api.schemas.ingredient import IngredientCreate, IngredientResponse
from app.database import get_db
from app.domain.models.ingredient import Ingredient

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


def get_ingredient_repo(db: AsyncSession = Depends(get_db)) -> IngredientRepository:
    return IngredientRepository(db)


@router.post("", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    body: IngredientCreate,
    repo: IngredientRepository = Depends(get_ingredient_repo),
) -> IngredientResponse:
    """Crea un nuevo ingrediente en el catálogo."""
    ingredient = Ingredient(
        id=0,
        name=body.name,
        aliases=body.aliases,
        category=body.category,
        storage_type=body.storage_type,
        unit=body.unit,
        protein_per_100g=body.protein_per_100g,
        calories_per_100g=body.calories_per_100g,
        avg_shelf_life_days=body.avg_shelf_life_days,
        created_at=datetime.utcnow(),
    )
    created = await repo.create_ingredient(ingredient)
    return IngredientResponse.model_validate(created.__dict__)


@router.get("", response_model=list[IngredientResponse])
async def list_ingredients(
    repo: IngredientRepository = Depends(get_ingredient_repo),
) -> list[IngredientResponse]:
    """Lista todos los ingredientes del catálogo."""
    ingredients = await repo.list_ingredients()
    return [IngredientResponse.model_validate(i.__dict__) for i in ingredients]


@router.get("/search", response_model=list[IngredientResponse])
async def search_ingredients(
    q: str = Query(..., min_length=2, description="Texto a buscar en nombre o alias"),
    repo: IngredientRepository = Depends(get_ingredient_repo),
) -> list[IngredientResponse]:
    """Busca ingredientes por nombre (insensible a mayúsculas)."""
    results = await repo.search_ingredients(q)
    return [IngredientResponse.model_validate(i.__dict__) for i in results]
