"""Modelo de dominio: precio de mercado de un ingrediente."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class MarketPrice:
    id: int
    ingredient_id: int
    price_ars: float
    source: str  # manual, sepa, scraping
    store: str | None  # Coto, Carrefour, Dia, etc.
    confidence: float  # 0.0-1.0
    date: date
    created_at: datetime
