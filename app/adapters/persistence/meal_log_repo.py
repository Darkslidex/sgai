"""Implementación SQLAlchemy del repositorio de meal_logs."""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.meal_log_orm import MealLogORM
from app.domain.models.meal_log import MealItem, MealLog


def _orm_to_domain(orm: MealLogORM) -> MealLog:
    items = [
        MealItem(
            ingredient=item["ingredient"],
            quantity_g=item["quantity_g"],
            calories_kcal=item["calories_kcal"],
            protein_g=item.get("protein_g"),
        )
        for item in (orm.items_json or [])
    ]
    return MealLog(
        id=orm.id,
        user_id=orm.user_id,
        date=orm.date,
        meal_type=orm.meal_type,
        raw_description=orm.raw_description,
        items=items,
        total_calories_kcal=orm.total_calories_kcal,
        total_protein_g=orm.total_protein_g,
        source=orm.source,
        notes=orm.notes,
        created_at=orm.created_at,
    )


class MealLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, meal_log: MealLog) -> MealLog:
        """Persiste un MealLog y retorna la versión guardada con id asignado."""
        items_json = [
            {
                "ingredient": item.ingredient,
                "quantity_g": item.quantity_g,
                "calories_kcal": item.calories_kcal,
                "protein_g": item.protein_g,
            }
            for item in meal_log.items
        ]
        orm = MealLogORM(
            user_id=meal_log.user_id,
            date=meal_log.date,
            meal_type=meal_log.meal_type,
            raw_description=meal_log.raw_description,
            items_json=items_json,
            total_calories_kcal=meal_log.total_calories_kcal,
            total_protein_g=meal_log.total_protein_g,
            source=meal_log.source,
            notes=meal_log.notes,
            created_at=datetime.utcnow(),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _orm_to_domain(orm)

    async def get_by_date(self, user_id: int, target_date: date) -> list[MealLog]:
        """Retorna todos los registros de comida de un usuario en una fecha."""
        result = await self._session.execute(
            select(MealLogORM)
            .where(
                MealLogORM.user_id == user_id,
                MealLogORM.date == target_date,
            )
            .order_by(MealLogORM.created_at.asc())
        )
        return [_orm_to_domain(row) for row in result.scalars()]

    async def get_daily_summary(self, user_id: int, target_date: date) -> dict:
        """Retorna resumen diario: total de calorías, proteínas y lista de comidas."""
        logs = await self.get_by_date(user_id, target_date)

        total_calories = sum(log.total_calories_kcal for log in logs)
        protein_values = [log.total_protein_g for log in logs if log.total_protein_g is not None]
        total_protein = round(sum(protein_values), 1) if protein_values else None

        meals = [
            {
                "id": log.id,
                "meal_type": log.meal_type,
                "raw_description": log.raw_description,
                "items": [
                    {
                        "ingredient": item.ingredient,
                        "quantity_g": item.quantity_g,
                        "calories_kcal": item.calories_kcal,
                        "protein_g": item.protein_g,
                    }
                    for item in log.items
                ],
                "total_calories_kcal": log.total_calories_kcal,
                "total_protein_g": log.total_protein_g,
                "source": log.source,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]

        return {
            "date": target_date.isoformat(),
            "user_id": user_id,
            "total_calories_kcal": round(total_calories, 1),
            "total_protein_g": total_protein,
            "meals": meals,
        }
