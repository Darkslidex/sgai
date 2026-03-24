"""
Placeholder para Health Connect API (Samsung Galaxy Watch 7 + S25).

ADR-003: Se implementa cuando los permisos de Google estén disponibles.
Por ahora, levanta NotImplementedError con mensaje informativo.
"""

from datetime import date

from app.domain.models.health import HealthLog
from app.domain.ports.health_data_port import HealthDataPort


class HealthConnectAdapter(HealthDataPort):
    """
    Placeholder para Health Connect API.

    ADR-003: Implementación futura cuando los permisos OAuth de Google Health Connect
    estén disponibles. El Samsung Galaxy Watch 7 + S25 sincroniza datos via esta API.
    """

    async def get_latest_metrics(self, user_id: int) -> HealthLog | None:
        raise NotImplementedError(
            "HealthConnectAdapter no está disponible todavía. "
            "ADR-003: Se activa cuando los permisos de Google Health Connect estén aprobados. "
            "Usá ManualHealthAdapter (input via /salud) mientras tanto."
        )

    async def get_metrics_range(
        self, user_id: int, start: date, end: date
    ) -> list[HealthLog]:
        raise NotImplementedError(
            "HealthConnectAdapter no está disponible todavía. "
            "ADR-003: Se activa cuando los permisos de Google Health Connect estén aprobados. "
            "Usá ManualHealthAdapter (input via /salud) mientras tanto."
        )
