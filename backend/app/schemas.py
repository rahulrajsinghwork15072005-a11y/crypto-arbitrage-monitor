"""Pydantic schemas for the arbitrage monitor API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FeeModel(BaseModel):
    taker: float = 0.001
    withdrawal: float = 0.0


class BookModel(BaseModel):
    venue: str
    symbol: str
    bids: list[tuple[float, float]] = Field(..., min_length=1)
    asks: list[tuple[float, float]] = Field(..., min_length=1)
    ts_exchange: float = 0.0
    ts_recv: float = 0.0


class DetectRequest(BaseModel):
    books: list[BookModel] = Field(..., min_length=2)
    fees: dict[str, FeeModel] = Field(default_factory=dict)
    now: float | None = None
    threshold: float = 0.0005
    min_qty: float = 0.05
    top_levels: int = 5
    max_age: float = 2.0


class RateEdge(BaseModel):
    from_currency: str = Field(..., alias="from")
    to: str
    rate: float = Field(..., gt=0)

    model_config = {"populate_by_name": True}


class ArbitrageGraphRequest(BaseModel):
    rates: list[RateEdge] = Field(..., min_length=2, description="Directed conversion edges")
    fee: float = Field(0.0, ge=0, lt=1, description="Proportional fee per leg")
    min_return: float = Field(0.0, description="Minimum net return to report a cycle")
