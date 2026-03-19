"""Port (interfaz abstracta) del repositorio de salud."""

from abc import ABC, abstractmethod
from datetime import date, datetime

from app.domain.models.health import HealthLog


class HealthRepositoryPort(ABC):
    @abstractmethod
    async def log_health(self, log: HealthLog) -> HealthLog: ...

    @abstractmethod
    async def get_logs(self, user_id: int, start: date, end: date) -> list[HealthLog]: ...

    @abstractmethod
    async def get_latest_log(self, user_id: int) -> HealthLog | None: ...

    @abstractmethod
    async def get_weekly_avg(self, user_id: int, week_start: date) -> dict: ...
