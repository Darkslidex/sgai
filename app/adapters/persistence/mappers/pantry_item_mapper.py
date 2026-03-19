"""Mapper: PantryItem ↔ PantryItemORM."""

from app.adapters.persistence.pantry_item_orm import PantryItemORM
from app.domain.models.pantry_item import PantryItem


def pantry_item_to_domain(orm: PantryItemORM) -> PantryItem:
    return PantryItem(
        id=orm.id,
        user_id=orm.user_id,
        ingredient_id=orm.ingredient_id,
        quantity_amount=orm.quantity_amount,
        unit=orm.unit,
        expires_at=orm.expires_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def pantry_item_to_orm(domain: PantryItem) -> PantryItemORM:
    return PantryItemORM(
        id=domain.id,
        user_id=domain.user_id,
        ingredient_id=domain.ingredient_id,
        quantity_amount=domain.quantity_amount,
        unit=domain.unit,
        expires_at=domain.expires_at,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )
