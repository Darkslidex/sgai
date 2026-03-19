"""Implementación SQLAlchemy del PlanningRepositoryPort."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.mappers.optimization_log_mapper import optimization_log_to_domain
from app.adapters.persistence.mappers.planning_mapper import weekly_plan_to_domain
from app.adapters.persistence.optimization_log_orm import OptimizationLogORM
from app.adapters.persistence.weekly_plan_orm import WeeklyPlanORM
from app.domain.models.optimization_log import OptimizationLog
from app.domain.models.planning import WeeklyPlan
from app.domain.ports.planning_repository import PlanningRepositoryPort


class PlanningRepository(PlanningRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_plan(self, plan: WeeklyPlan) -> WeeklyPlan:
        # Desactivar planes activos anteriores del usuario
        await self._session.execute(
            update(WeeklyPlanORM)
            .where(WeeklyPlanORM.user_id == plan.user_id, WeeklyPlanORM.is_active.is_(True))
            .values(is_active=False)
        )
        orm = WeeklyPlanORM(
            user_id=plan.user_id,
            week_start=plan.week_start,
            plan_json=plan.plan_json,
            shopping_list_json=plan.shopping_list_json,
            total_cost_ars=plan.total_cost_ars,
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=plan.expires_at,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return weekly_plan_to_domain(orm)

    async def get_active_plan(self, user_id: int) -> WeeklyPlan | None:
        result = await self._session.execute(
            select(WeeklyPlanORM).where(
                WeeklyPlanORM.user_id == user_id,
                WeeklyPlanORM.is_active.is_(True),
            )
        )
        orm = result.scalar_one_or_none()
        return weekly_plan_to_domain(orm) if orm else None

    async def get_plan_history(self, user_id: int, limit: int = 10) -> list[WeeklyPlan]:
        result = await self._session.execute(
            select(WeeklyPlanORM)
            .where(WeeklyPlanORM.user_id == user_id)
            .order_by(WeeklyPlanORM.created_at.desc())
            .limit(limit)
        )
        return [weekly_plan_to_domain(row) for row in result.scalars()]

    async def log_optimization(self, log: OptimizationLog) -> OptimizationLog:
        orm = OptimizationLogORM(
            user_id=log.user_id,
            week_start=log.week_start,
            feedback=log.feedback,
            optimization_data=log.optimization_data,
            created_at=datetime.utcnow(),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return optimization_log_to_domain(orm)

    async def get_optimization_history(self, user_id: int, limit: int = 10) -> list[OptimizationLog]:
        result = await self._session.execute(
            select(OptimizationLogORM)
            .where(OptimizationLogORM.user_id == user_id)
            .order_by(OptimizationLogORM.created_at.desc())
            .limit(limit)
        )
        return [optimization_log_to_domain(row) for row in result.scalars()]
