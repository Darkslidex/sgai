"""
Servicio de Pantry — CRUD de alacena con control de vencimientos.

Maneja el inventario físico del usuario con seguimiento de fechas de caducidad.
"""

import logging
from datetime import date, datetime

from app.domain.models.pantry_item import PantryItem
from app.domain.ports.ingredient_repository import IngredientRepositoryPort
from app.domain.ports.market_repository import MarketRepositoryPort

logger = logging.getLogger(__name__)


class PantryService:
    """Gestiona el inventario de alacena del usuario.

    - add_item: agrega cantidad (suma a existente o crea nuevo)
    - remove_item: resta cantidad (elimina si llega a 0)
    - get_expiring_soon: items próximos a vencer
    - get_expired: items ya vencidos → sugerir descarte
    """

    def __init__(
        self,
        market_repo: MarketRepositoryPort,
        ingredient_repo: IngredientRepositoryPort,
    ) -> None:
        self._market_repo = market_repo
        self._ingredient_repo = ingredient_repo

    async def add_item(
        self,
        user_id: int,
        ingredient_id: int,
        quantity: float,
        expiry_date: date | None = None,
    ) -> PantryItem:
        """Agrega cantidad al inventario. Si el item ya existe, suma la cantidad.

        Args:
            user_id: ID del usuario.
            ingredient_id: ID del ingrediente.
            quantity: Cantidad a agregar (en la unidad del ingrediente).
            expiry_date: Fecha de vencimiento (actualiza si se especifica).

        Returns:
            PantryItem actualizado o creado.

        Raises:
            ValueError: Si el ingrediente no existe.
        """
        if quantity <= 0:
            raise ValueError("La cantidad a agregar debe ser positiva.")

        existing = await self._market_repo.get_pantry_item(user_id, ingredient_id)

        expires_dt: datetime | None = None
        if expiry_date is not None:
            expires_dt = datetime.combine(expiry_date, datetime.min.time())

        if existing is None:
            ingredient = await self._ingredient_repo.get_ingredient(ingredient_id)
            if ingredient is None:
                raise ValueError(f"Ingrediente {ingredient_id} no encontrado.")
            new_item = PantryItem(
                id=0,
                user_id=user_id,
                ingredient_id=ingredient_id,
                quantity_amount=quantity,
                unit=ingredient.unit,
                expires_at=expires_dt,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        else:
            new_item = PantryItem(
                id=existing.id,
                user_id=existing.user_id,
                ingredient_id=existing.ingredient_id,
                quantity_amount=existing.quantity_amount + quantity,
                unit=existing.unit,
                expires_at=expires_dt if expires_dt is not None else existing.expires_at,
                created_at=existing.created_at,
                updated_at=datetime.utcnow(),
            )

        saved = await self._market_repo.update_pantry(new_item)
        logger.info(
            "Pantry add_item: user_id=%d, ingredient_id=%d, +%.2f %s → total=%.2f",
            user_id, ingredient_id, quantity, saved.unit, saved.quantity_amount,
        )
        return saved

    async def remove_item(
        self,
        user_id: int,
        ingredient_id: int,
        quantity: float,
    ) -> PantryItem | None:
        """Resta cantidad del inventario. Elimina el item si la cantidad llega a 0.

        Args:
            user_id: ID del usuario.
            ingredient_id: ID del ingrediente.
            quantity: Cantidad a consumir/descartar.

        Returns:
            PantryItem actualizado, o None si fue eliminado.
        """
        if quantity <= 0:
            raise ValueError("La cantidad a remover debe ser positiva.")

        existing = await self._market_repo.get_pantry_item(user_id, ingredient_id)
        if existing is None:
            logger.warning(
                "remove_item: ingredient_id=%d no está en el pantry de user_id=%d",
                ingredient_id, user_id,
            )
            return None

        new_quantity = existing.quantity_amount - quantity
        if new_quantity <= 0:
            await self._market_repo.delete_pantry_item(user_id, ingredient_id)
            logger.info(
                "Pantry remove_item: user_id=%d, ingredient_id=%d eliminado (consumido).",
                user_id, ingredient_id,
            )
            return None

        updated = PantryItem(
            id=existing.id,
            user_id=existing.user_id,
            ingredient_id=existing.ingredient_id,
            quantity_amount=new_quantity,
            unit=existing.unit,
            expires_at=existing.expires_at,
            created_at=existing.created_at,
            updated_at=datetime.utcnow(),
        )
        result = await self._market_repo.update_pantry(updated)
        logger.info(
            "Pantry remove_item: user_id=%d, ingredient_id=%d, -%.2f → quedan=%.2f %s",
            user_id, ingredient_id, quantity, result.quantity_amount, result.unit,
        )
        return result

    async def get_expiring_soon(self, user_id: int, days: int = 3) -> list[PantryItem]:
        """Retorna items que vencen en los próximos N días (sin incluir los ya vencidos).

        Args:
            user_id: ID del usuario.
            days: Días hacia adelante a verificar (default 3).

        Returns:
            Lista de PantryItem ordenada por fecha de vencimiento ascendente.
        """
        items = await self._market_repo.get_expiring_pantry(user_id, days=days)
        logger.debug(
            "get_expiring_soon: user_id=%d, días=%d → %d items encontrados",
            user_id, days, len(items),
        )
        return items

    async def get_expired(self, user_id: int) -> list[PantryItem]:
        """Retorna items ya vencidos → sugerir descarte.

        Args:
            user_id: ID del usuario.

        Returns:
            Lista de PantryItem vencidos.
        """
        items = await self._market_repo.get_expired_pantry(user_id)
        if items:
            logger.warning(
                "get_expired: user_id=%d tiene %d items vencidos en el pantry.",
                user_id, len(items),
            )
        return items
