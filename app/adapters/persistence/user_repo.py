"""Implementación SQLAlchemy del UserRepositoryPort."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers.user_preference_mapper import (
    user_preference_to_domain,
    user_preference_to_orm,
)
from app.adapters.persistence.mappers.user_profile_mapper import user_profile_to_domain
from app.adapters.persistence.user_preference_orm import UserPreferenceORM
from app.adapters.persistence.user_profile_orm import UserProfileORM
from app.domain.models.user import UserProfile
from app.domain.models.user_preference import UserPreference
from app.domain.ports.user_repository import UserRepositoryPort


class UserRepository(UserRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self, user_id: int) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfileORM).where(UserProfileORM.id == user_id)
        )
        orm = result.scalar_one_or_none()
        return user_profile_to_domain(orm) if orm else None

    async def get_profile_by_chat_id(self, telegram_chat_id: str) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfileORM).where(UserProfileORM.telegram_chat_id == telegram_chat_id)
        )
        orm = result.scalar_one_or_none()
        return user_profile_to_domain(orm) if orm else None

    async def create_profile(self, profile: UserProfile) -> UserProfile:
        now = datetime.utcnow()
        orm = UserProfileORM(
            telegram_chat_id=profile.telegram_chat_id,
            name=profile.name,
            age=profile.age,
            weight_kg=profile.weight_kg,
            height_cm=profile.height_cm,
            activity_level=profile.activity_level,
            goal=profile.goal,
            max_storage_volume=profile.max_storage_volume,
            created_at=now,
            updated_at=now,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return user_profile_to_domain(orm)

    async def update_profile(self, profile: UserProfile) -> UserProfile:
        result = await self._session.execute(
            select(UserProfileORM).where(UserProfileORM.id == profile.id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            raise ValueError(f"UserProfile {profile.id} not found")
        orm.name = profile.name
        orm.age = profile.age
        orm.weight_kg = profile.weight_kg
        orm.height_cm = profile.height_cm
        orm.activity_level = profile.activity_level
        orm.goal = profile.goal
        orm.max_storage_volume = profile.max_storage_volume
        orm.updated_at = datetime.utcnow()
        await self._session.flush()
        await self._session.refresh(orm)
        return user_profile_to_domain(orm)

    async def get_preferences(self, user_id: int) -> list[UserPreference]:
        result = await self._session.execute(
            select(UserPreferenceORM).where(UserPreferenceORM.user_id == user_id)
        )
        return [user_preference_to_domain(row) for row in result.scalars()]

    async def set_preference(self, pref: UserPreference) -> UserPreference:
        # Upsert: si existe la clave para el usuario, actualizar; si no, crear
        result = await self._session.execute(
            select(UserPreferenceORM).where(
                UserPreferenceORM.user_id == pref.user_id,
                UserPreferenceORM.key == pref.key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = pref.value
            await self._session.flush()
            await self._session.refresh(existing)
            return user_preference_to_domain(existing)
        orm = UserPreferenceORM(
            user_id=pref.user_id,
            key=pref.key,
            value=pref.value,
            created_at=datetime.utcnow(),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return user_preference_to_domain(orm)

    async def delete_preference(self, pref_id: int) -> bool:
        result = await self._session.execute(
            select(UserPreferenceORM).where(UserPreferenceORM.id == pref_id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return False
        await self._session.delete(orm)
        await self._session.flush()
        return True
