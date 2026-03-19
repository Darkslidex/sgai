"""Mapper: WeeklyPlan ↔ WeeklyPlanORM."""

from app.adapters.persistence.weekly_plan_orm import WeeklyPlanORM
from app.domain.models.planning import WeeklyPlan


def weekly_plan_to_domain(orm: WeeklyPlanORM) -> WeeklyPlan:
    return WeeklyPlan(
        id=orm.id,
        user_id=orm.user_id,
        week_start=orm.week_start,
        plan_json=orm.plan_json or {},
        shopping_list_json=orm.shopping_list_json or {},
        total_cost_ars=orm.total_cost_ars,
        is_active=orm.is_active,
        created_at=orm.created_at,
        expires_at=orm.expires_at,
    )


def weekly_plan_to_orm(domain: WeeklyPlan) -> WeeklyPlanORM:
    return WeeklyPlanORM(
        id=domain.id,
        user_id=domain.user_id,
        week_start=domain.week_start,
        plan_json=domain.plan_json,
        shopping_list_json=domain.shopping_list_json,
        total_cost_ars=domain.total_cost_ars,
        is_active=domain.is_active,
        created_at=domain.created_at,
        expires_at=domain.expires_at,
    )
