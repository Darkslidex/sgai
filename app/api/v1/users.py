"""Endpoints CRUD para perfiles de usuario y preferencias."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.user_repo import UserRepository
from app.api.schemas.user import (
    UserPreferenceCreate,
    UserPreferenceResponse,
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.database import get_db
from app.domain.models.user import UserProfile
from app.domain.models.user_preference import UserPreference

router = APIRouter(prefix="/users", tags=["users"])


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


@router.post("/profile", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: UserProfileCreate,
    repo: UserRepository = Depends(get_user_repo),
) -> UserProfileResponse:
    """Crea un nuevo perfil de usuario."""
    profile = UserProfile(
        id=0,
        telegram_chat_id=body.telegram_chat_id,
        name=body.name,
        age=body.age,
        weight_kg=body.weight_kg,
        height_cm=body.height_cm,
        activity_level=body.activity_level,
        goal=body.goal,
        max_storage_volume=body.max_storage_volume,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    created = await repo.create_profile(profile)
    return UserProfileResponse.model_validate(created.__dict__)


@router.get("/profile/{user_id}", response_model=UserProfileResponse)
async def get_profile(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
) -> UserProfileResponse:
    """Obtiene el perfil de un usuario por su ID."""
    profile = await repo.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    return UserProfileResponse.model_validate(profile.__dict__)


@router.put("/profile/{user_id}", response_model=UserProfileResponse)
async def update_profile(
    user_id: int,
    body: UserProfileUpdate,
    repo: UserRepository = Depends(get_user_repo),
) -> UserProfileResponse:
    """Actualiza el perfil de un usuario."""
    existing = await repo.get_profile(user_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    updated_profile = UserProfile(
        id=existing.id,
        telegram_chat_id=existing.telegram_chat_id,
        name=body.name if body.name is not None else existing.name,
        age=body.age if body.age is not None else existing.age,
        weight_kg=body.weight_kg if body.weight_kg is not None else existing.weight_kg,
        height_cm=body.height_cm if body.height_cm is not None else existing.height_cm,
        activity_level=body.activity_level if body.activity_level is not None else existing.activity_level,
        goal=body.goal if body.goal is not None else existing.goal,
        max_storage_volume=(
            body.max_storage_volume if body.max_storage_volume is not None else existing.max_storage_volume
        ),
        created_at=existing.created_at,
        updated_at=existing.updated_at,
    )
    result = await repo.update_profile(updated_profile)
    return UserProfileResponse.model_validate(result.__dict__)


@router.get("/preferences/{user_id}", response_model=list[UserPreferenceResponse])
async def get_preferences(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
) -> list[UserPreferenceResponse]:
    """Lista las preferencias/restricciones de un usuario."""
    prefs = await repo.get_preferences(user_id)
    return [UserPreferenceResponse.model_validate(p.__dict__) for p in prefs]


@router.post("/preferences", response_model=UserPreferenceResponse, status_code=status.HTTP_201_CREATED)
async def set_preference(
    body: UserPreferenceCreate,
    repo: UserRepository = Depends(get_user_repo),
) -> UserPreferenceResponse:
    """Agrega o actualiza una preferencia del usuario (upsert por clave)."""
    pref = UserPreference(
        id=0,
        user_id=body.user_id,
        key=body.key,
        value=body.value,
        created_at=datetime.utcnow(),
    )
    result = await repo.set_preference(pref)
    return UserPreferenceResponse.model_validate(result.__dict__)


@router.delete("/preferences/{pref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preference(
    pref_id: int,
    repo: UserRepository = Depends(get_user_repo),
) -> None:
    """Elimina una preferencia por ID."""
    deleted = await repo.delete_preference(pref_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferencia no encontrada")
