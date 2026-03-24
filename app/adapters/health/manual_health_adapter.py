"""
Adapter primario funcional para datos biométricos.

Lee datos de health_logs ingresados manualmente vía Telegram (/salud).
Es el adapter activo hasta que HealthConnect esté disponible (ADR-003).
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.health_repo import HealthRepository
from app.domain.models.health import HealthLog
from app.domain.ports.health_data_port import HealthDataPort


class ManualHealthAdapter(HealthDataPort):
    """
    Adapter primario funcional.
    Lee datos de health_logs ingresados vía Telegram (/salud).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = HealthRepository(session)

    async def get_latest_metrics(self, user_id: int) -> HealthLog | None:
        """Retorna el log de salud más reciente del usuario, o None si no hay datos."""
        return await self._repo.get_latest_log(user_id)

    async def get_metrics_range(
        self, user_id: int, start: date, end: date
    ) -> list[HealthLog]:
        """Retorna logs de salud en el rango de fechas especificado."""
        return await self._repo.get_logs(user_id, start, end)
