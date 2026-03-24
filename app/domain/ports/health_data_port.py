"""Port (interfaz abstracta) para fuentes de datos biométricos."""

from abc import ABC, abstractmethod
from datetime import date

from app.domain.models.health import HealthLog


class HealthDataPort(ABC):
    """Interfaz para obtener datos biométricos. Implementaciones: Health Connect o input manual."""

    @abstractmethod
    async def get_latest_metrics(self, user_id: int) -> HealthLog | None: ...

    @abstractmethod
    async def get_metrics_range(
        self, user_id: int, start: date, end: date
    ) -> list[HealthLog]: ...
