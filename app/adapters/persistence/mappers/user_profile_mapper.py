"""Mapper: UserProfile ↔ UserProfileORM."""

from app.adapters.persistence.user_profile_orm import UserProfileORM
from app.domain.models.user import UserProfile


def user_profile_to_domain(orm: UserProfileORM) -> UserProfile:
    return UserProfile(
        id=orm.id,
        telegram_chat_id=orm.telegram_chat_id,
        name=orm.name,
        age=orm.age,
        weight_kg=orm.weight_kg,
        height_cm=orm.height_cm,
        activity_level=orm.activity_level,
        goal=orm.goal,
        max_storage_volume=orm.max_storage_volume or {},
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def user_profile_to_orm(domain: UserProfile) -> UserProfileORM:
    return UserProfileORM(
        id=domain.id,
        telegram_chat_id=domain.telegram_chat_id,
        name=domain.name,
        age=domain.age,
        weight_kg=domain.weight_kg,
        height_cm=domain.height_cm,
        activity_level=domain.activity_level,
        goal=domain.goal,
        max_storage_volume=domain.max_storage_volume,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )
