"""Mapper: OptimizationLog ↔ OptimizationLogORM."""

from app.adapters.persistence.optimization_log_orm import OptimizationLogORM
from app.domain.models.optimization_log import OptimizationLog


def optimization_log_to_domain(orm: OptimizationLogORM) -> OptimizationLog:
    return OptimizationLog(
        id=orm.id,
        user_id=orm.user_id,
        week_start=orm.week_start,
        feedback=orm.feedback,
        optimization_data=orm.optimization_data or {},
        created_at=orm.created_at,
    )


def optimization_log_to_orm(domain: OptimizationLog) -> OptimizationLogORM:
    return OptimizationLogORM(
        id=domain.id,
        user_id=domain.user_id,
        week_start=domain.week_start,
        feedback=domain.feedback,
        optimization_data=domain.optimization_data,
        created_at=domain.created_at,
    )
