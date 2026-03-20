"""
Cliente HTTP para consumir la API de FastAPI de SGAI.

Centraliza todas las llamadas HTTP. Maneja timeouts y errores sin crashear el dashboard.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from dashboard.config import get_dashboard_settings

logger = logging.getLogger(__name__)


class SGAIClient:
    """Cliente síncrono para la API REST de SGAI."""

    def __init__(self, base_url: str | None = None) -> None:
        cfg = get_dashboard_settings()
        self._base_url = base_url or cfg.api_base_url
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=10.0,
            headers={"Content-Type": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SGAIClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Internal ────────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict | list | None:
        """GET request. Retorna None en caso de error."""
        try:
            resp = self._client.get(path, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("Timeout en GET %s", path)
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning("HTTP %d en GET %s", exc.response.status_code, path)
            return None
        except Exception as exc:
            logger.warning("Error en GET %s: %s", path, exc)
            return None

    def _post(self, path: str, data: dict) -> dict | None:
        """POST request. Retorna None en caso de error."""
        try:
            resp = self._client.post(path, json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Error en POST %s: %s", path, exc)
            return None

    def _put(self, path: str, data: dict) -> dict | None:
        try:
            resp = self._client.put(path, json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Error en PUT %s: %s", path, exc)
            return None

    # ── Users ────────────────────────────────────────────────────────────────

    def get_profile(self, user_id: int) -> dict | None:
        return self._get(f"/api/v1/users/{user_id}")

    def update_profile(self, user_id: int, data: dict) -> dict | None:
        return self._put(f"/api/v1/users/{user_id}", data)

    def get_preferences(self, user_id: int) -> list[dict]:
        result = self._get(f"/api/v1/users/{user_id}/preferences")
        return result if isinstance(result, list) else []

    # ── Health ───────────────────────────────────────────────────────────────

    def get_tdee(self, user_id: int) -> dict | None:
        return self._get(f"/api/v1/health/tdee/{user_id}")

    def get_energy_state(self, user_id: int) -> dict | None:
        return self._get(f"/api/v1/health/energy-state/{user_id}")

    def get_health_logs(self, user_id: int, days: int = 30) -> list[dict]:
        result = self._get(f"/api/v1/health/{user_id}/logs")
        return result if isinstance(result, list) else []

    def get_latest_health_log(self, user_id: int) -> dict | None:
        return self._get(f"/api/v1/health/{user_id}/latest")

    def get_weekly_avg(self, user_id: int) -> dict | None:
        return self._get(f"/api/v1/health/{user_id}/weekly-avg")

    # ── Market / Prices ──────────────────────────────────────────────────────

    def get_current_prices(self) -> list[dict]:
        result = self._get("/api/v1/market/prices/current")
        return result if isinstance(result, list) else []

    def get_price_history(self, ingredient_id: int) -> list[dict]:
        result = self._get(f"/api/v1/market/prices/history/{ingredient_id}")
        return result if isinstance(result, list) else []

    def add_price(self, ingredient_id: int, price_ars: float, source: str = "manual") -> dict | None:
        return self._post("/api/v1/market/prices", {
            "ingredient_id": ingredient_id,
            "price_ars": price_ars,
            "source": source,
        })

    # ── Pantry ───────────────────────────────────────────────────────────────

    def get_pantry(self, user_id: int) -> list[dict]:
        result = self._get(f"/api/v1/market/pantry/{user_id}")
        return result if isinstance(result, list) else []

    def update_pantry(self, user_id: int, ingredient_id: int, quantity: float, unit: str) -> dict | None:
        return self._post("/api/v1/market/pantry", {
            "user_id": user_id,
            "ingredient_id": ingredient_id,
            "quantity_amount": quantity,
            "unit": unit,
        })

    # ── Planning ─────────────────────────────────────────────────────────────

    def get_active_plan(self, user_id: int) -> dict | None:
        result = self._get(f"/api/v1/planning/{user_id}/active")
        return result if isinstance(result, dict) else None

    def get_plan_history(self, user_id: int) -> list[dict]:
        result = self._get(f"/api/v1/planning/{user_id}/history")
        return result if isinstance(result, list) else []

    # ── Ingredients ──────────────────────────────────────────────────────────

    def get_ingredients(self) -> list[dict]:
        result = self._get("/api/v1/ingredients")
        return result if isinstance(result, list) else []

    # ── System Health ─────────────────────────────────────────────────────────

    def get_system_health(self) -> dict | None:
        return self._get("/health")

    def is_api_reachable(self) -> bool:
        result = self.get_system_health()
        return result is not None


def get_client() -> SGAIClient:
    """Factory — crea un cliente con config del entorno."""
    return SGAIClient()
