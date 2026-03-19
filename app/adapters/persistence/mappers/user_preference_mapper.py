"""Mapper: UserPreference ↔ UserPreferenceORM."""

from app.adapters.persistence.user_preference_orm import UserPreferenceORM
from app.domain.models.user_preference import UserPreference


def user_preference_to_domain(orm: UserPreferenceORM) -> UserPreference:
    return UserPreference(
        id=orm.id,
        user_id=orm.user_id,
        key=orm.key,
        value=orm.value,
        created_at=orm.created_at,
    )


def user_preference_to_orm(domain: UserPreference) -> UserPreferenceORM:
    return UserPreferenceORM(
        id=domain.id,
        user_id=domain.user_id,
        key=domain.key,
        value=domain.value,
        created_at=domain.created_at,
    )
