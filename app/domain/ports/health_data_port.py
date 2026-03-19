"""Port (interfaz abstracta) para fuentes de datos biométricos."""

from abc import ABC, abstractmethod

from app.domain.models.health import HealthLog


class HealthDataPort(ABC):
    """Interfaz para obtener datos biométricos. Implementaciones: Health Connect o input manual."""

    @abstractmethod
    async def sync_health_data(self, user_id: int) -> list[HealthLog]: ...

    @abstractmethod
    async def get_latest_metrics(self, user_id: int) -> dict: ...
