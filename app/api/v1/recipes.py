"""Endpoints CRUD para recetas."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.recipe_repo import RecipeRepository
from app.api.schemas.recipe import RecipeCreate, RecipeIngredientResponse, RecipeResponse
from app.database import get_db
from app.domain.models.recipe import Recipe
from app.domain.models.recipe_ingredient import RecipeIngredient

router = APIRouter(prefix="/recipes", tags=["recipes"])


def get_recipe_repo(db: AsyncSession = Depends(get_db)) -> RecipeRepository:
    return RecipeRepository(db)


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    body: RecipeCreate,
    repo: RecipeRepository = Depends(get_recipe_repo),
) -> RecipeResponse:
    """Crea una receta junto con sus ingredientes."""
    recipe = Recipe(
        id=0,
        name=body.name,
        description=body.description,
        prep_time_minutes=body.prep_time_minutes,
        is_batch_friendly=body.is_batch_friendly,
        reheatable_days=body.reheatable_days,
        servings=body.servings,
        calories_per_serving=body.calories_per_serving,
        protein_per_serving=body.protein_per_serving,
        carbs_per_serving=body.carbs_per_serving,
        fat_per_serving=body.fat_per_serving,
        instructions=body.instructions,
        tags=body.tags,
        created_at=datetime.utcnow(),
    )
    ingredients = [
        RecipeIngredient(
            id=0,
            recipe_id=0,
            ingredient_id=ing.ingredient_id,
            quantity_amount=ing.quantity_amount,
            unit=ing.unit,
        )
        for ing in body.ingredients
    ]
    created = await repo.create_recipe(recipe, ingredients)
    return RecipeResponse.model_validate(created.__dict__)


@router.get("/overlapping", response_model=list[RecipeResponse])
async def get_overlapping_recipes(
    ingredient_ids: str = Query(..., description="IDs separados por coma: 1,2,3"),
    min_overlap: int = Query(2, ge=1, description="Mínimo de ingredientes en común"),
    repo: RecipeRepository = Depends(get_recipe_repo),
) -> list[RecipeResponse]:
    """Busca recetas que compartan al menos min_overlap ingredientes de la lista dada."""
    ids = [int(i.strip()) for i in ingredient_ids.split(",") if i.strip()]
    if not ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ingredient_ids vacío")
    recipes = await repo.get_overlapping_recipes(ids, min_overlap)
    return [RecipeResponse.model_validate(r.__dict__) for r in recipes]


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: int,
    repo: RecipeRepository = Depends(get_recipe_repo),
) -> RecipeResponse:
    """Obtiene una receta por su ID."""
    recipe = await repo.get_recipe(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    return RecipeResponse.model_validate(recipe.__dict__)


@router.get("", response_model=list[RecipeResponse])
async def list_recipes(
    is_batch_friendly: bool | None = Query(None, description="Filtrar por batch cooking"),
    max_prep_time: int | None = Query(None, ge=1, description="Tiempo máximo de preparación (min)"),
    min_reheatable_days: int | None = Query(None, ge=1, le=5, description="Mínimo de días recalentable"),
    repo: RecipeRepository = Depends(get_recipe_repo),
) -> list[RecipeResponse]:
    """Lista recetas con filtros opcionales."""
    filters: dict = {}
    if is_batch_friendly is not None:
        filters["is_batch_friendly"] = is_batch_friendly
    if max_prep_time is not None:
        filters["max_prep_time"] = max_prep_time
    if min_reheatable_days is not None:
        filters["min_reheatable_days"] = min_reheatable_days
    recipes = await repo.list_recipes(filters or None)
    return [RecipeResponse.model_validate(r.__dict__) for r in recipes]
