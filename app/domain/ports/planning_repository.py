"""Port (interfaz abstracta) del repositorio de planificación."""

from abc import ABC, abstractmethod

from app.domain.models.optimization_log import OptimizationLog
from app.domain.models.planning import WeeklyPlan


class PlanningRepositoryPort(ABC):
    @abstractmethod
    async def save_plan(self, plan: WeeklyPlan) -> WeeklyPlan: ...

    @abstractmethod
    async def get_active_plan(self, user_id: int) -> WeeklyPlan | None: ...

    @abstractmethod
    async def get_plan_history(self, user_id: int, limit: int = 10) -> list[WeeklyPlan]: ...

    @abstractmethod
    async def log_optimization(self, log: OptimizationLog) -> OptimizationLog: ...

    @abstractmethod
    async def get_optimization_history(self, user_id: int, limit: int = 10) -> list[OptimizationLog]: ...
