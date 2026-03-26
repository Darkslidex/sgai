"""Implementación SQLAlchemy del HealthRepositoryPort."""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.health_log_orm import HealthLogORM
from app.adapters.persistence.mappers.health_log_mapper import health_log_to_domain
from app.domain.models.health import HealthLog
from app.domain.ports.health_repository import HealthRepositoryPort


class HealthRepository(HealthRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_health(self, log: HealthLog) -> HealthLog:
        orm = HealthLogORM(
            user_id=log.user_id,
            date=log.date,
            sleep_score=log.sleep_score,
            stress_level=log.stress_level,
            hrv=log.hrv,
            steps=log.steps,
            mood=log.mood,
            notes=log.notes,
            source=log.source,
            created_at=datetime.utcnow(),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return health_log_to_domain(orm)

    async def upsert_daily_log(self, log: HealthLog) -> HealthLog:
        """Upsert: actualiza el registro del dia si existe, o inserta uno nuevo.

        Fusiona los campos no-nulos del log entrante con los del registro existente.
        Evita duplicados cuando Ana y el sync de Google Fit registran el mismo dia.
        """
        result = await self._session.execute(
            select(HealthLogORM)
            .where(
                HealthLogORM.user_id == log.user_id,
                HealthLogORM.date == log.date,
            )
            .order_by(HealthLogORM.created_at.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            return await self.log_health(log)

        if log.sleep_score is not None:
            existing.sleep_score = log.sleep_score
        if log.stress_level is not None:
            existing.stress_level = log.stress_level
        if log.hrv is not None:
            existing.hrv = log.hrv
        if log.steps is not None:
            existing.steps = log.steps
        if log.mood is not None:
            existing.mood = log.mood
        if log.notes:
            existing.notes = log.notes
        existing.source = log.source

        await self._session.flush()
        await self._session.refresh(existing)
        return health_log_to_domain(existing)

    async def get_logs(self, user_id: int, start: date, end: date) -> list[HealthLog]:
        result = await self._session.execute(
            select(HealthLogORM)
            .where(
                HealthLogORM.user_id == user_id,
                HealthLogORM.date >= start,
                HealthLogORM.date <= end,
            )
            .order_by(HealthLogORM.date.desc())
        )
        return [health_log_to_domain(row) for row in result.scalars()]

    async def get_latest_log(self, user_id: int) -> HealthLog | None:
        result = await self._session.execute(
            select(HealthLogORM)
            .where(HealthLogORM.user_id == user_id)
            .order_by(HealthLogORM.date.desc(), HealthLogORM.created_at.desc())
            .limit(1)
        )
        orm = result.scalar_one_or_none()
        return health_log_to_domain(orm) if orm else None

    async def get_weekly_avg(self, user_id: int, week_start: date) -> dict:
        week_end = week_start + timedelta(days=6)
        result = await self._session.execute(
            select(
                func.avg(HealthLogORM.sleep_score).label("avg_sleep_score"),
                func.avg(HealthLogORM.stress_level).label("avg_stress_level"),
                func.avg(HealthLogORM.hrv).label("avg_hrv"),
                func.avg(HealthLogORM.steps).label("avg_steps"),
            ).where(
                HealthLogORM.user_id == user_id,
                HealthLogORM.date >= week_start,
                HealthLogORM.date <= week_end,
            )
        )
        row = result.one()
        return {
            "avg_sleep_score": row.avg_sleep_score,
            "avg_stress_level": row.avg_stress_level,
            "avg_hrv": row.avg_hrv,
            "avg_steps": row.avg_steps,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
        }
