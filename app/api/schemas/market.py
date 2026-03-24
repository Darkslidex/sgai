"""Schemas Pydantic para precios de mercado y despensa."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketPriceCreate(BaseModel):
    ingredient_id: int
    price_ars: float = Field(gt=0, le=1_000_000)
    source: Literal["manual", "sepa", "scraping"] = "manual"
    store: str | None = Field(None, max_length=100)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    date: date


class MarketPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: int
    price_ars: float
    source: str
    store: str | None
    confidence: float
    date: date
    created_at: datetime


class StorePrice(BaseModel):
    store: str | None
    price_ars: float
    date: date
    source: str


class CheapestPriceResponse(BaseModel):
    ingredient_name: str
    ingredient_id: int
    cheapest_price_ars: float
    cheapest_store: str | None
    cheapest_date: date
    store_comparison: list[StorePrice]
    days_analyzed: int


class PriceHistoryStats(BaseModel):
    ingredient_name: str
    ingredient_id: int
    days_analyzed: int
    total_records: int
    avg_ars: float | None
    min_ars: float | None
    max_ars: float | None
    history: list[MarketPriceResponse]


class PantryItemCreate(BaseModel):
    user_id: int
    ingredient_id: int
    quantity_amount: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=20)
    expires_at: datetime | None = None


class PantryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    ingredient_id: int
    quantity_amount: float
    unit: str
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
