"""Normalized order-book model shared across venues."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Level:
    price: float
    size: float


@dataclass(frozen=True)
class OrderBook:
    """A venue's normalized book. ``bids`` desc by price, ``asks`` asc by price."""

    venue: str
    symbol: str
    bids: list[Level]
    asks: list[Level]
    ts_exchange: float
    ts_recv: float

    def __post_init__(self) -> None:
        if not self.bids or not self.asks:
            raise ValueError("order book must have at least one bid and one ask")

    @property
    def best_bid(self) -> float:
        return self.bids[0].price

    @property
    def best_ask(self) -> float:
        return self.asks[0].price

    @property
    def mid(self) -> float:
        return 0.5 * (self.best_bid + self.best_ask)

    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid

    def depth(self, side: str, levels: int) -> float:
        """Total size available within the top ``levels`` on a side."""
        book_side = self.bids if side == "bid" else self.asks
        return float(sum(level.size for level in book_side[:levels]))


def book_from_dict(d: dict) -> OrderBook:
    """Build an :class:`OrderBook` from a plain dict (API payloads)."""
    return OrderBook(
        venue=d["venue"],
        symbol=d["symbol"],
        bids=[Level(float(p), float(s)) for p, s in d["bids"]],
        asks=[Level(float(p), float(s)) for p, s in d["asks"]],
        ts_exchange=float(d.get("ts_exchange", 0.0)),
        ts_recv=float(d.get("ts_recv", 0.0)),
    )
