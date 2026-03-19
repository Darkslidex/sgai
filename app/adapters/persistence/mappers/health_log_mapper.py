"""Mapper: HealthLog ↔ HealthLogORM."""

from app.adapters.persistence.health_log_orm import HealthLogORM
from app.domain.models.health import HealthLog


def health_log_to_domain(orm: HealthLogORM) -> HealthLog:
    return HealthLog(
        id=orm.id,
        user_id=orm.user_id,
        date=orm.date,
        sleep_score=orm.sleep_score,
        stress_level=orm.stress_level,
        hrv=orm.hrv,
        steps=orm.steps,
        mood=orm.mood,
        notes=orm.notes,
        source=orm.source,
        created_at=orm.created_at,
    )


def health_log_to_orm(domain: HealthLog) -> HealthLogORM:
    return HealthLogORM(
        id=domain.id,
        user_id=domain.user_id,
        date=domain.date,
        sleep_score=domain.sleep_score,
        stress_level=domain.stress_level,
        hrv=domain.hrv,
        steps=domain.steps,
        mood=domain.mood,
        notes=domain.notes,
        source=domain.source,
        created_at=domain.created_at,
    )
