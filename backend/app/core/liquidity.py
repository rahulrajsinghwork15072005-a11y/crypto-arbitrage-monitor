"""Liquidity and freshness (staleness) filters."""
from __future__ import annotations

from .book import OrderBook


def passes_liquidity(book: OrderBook, min_qty: float, top_levels: int = 5) -> bool:
    """Both sides must offer at least ``min_qty`` within the top ``top_levels``."""
    return (
        book.depth("bid", top_levels) >= min_qty
        and book.depth("ask", top_levels) >= min_qty
    )


def is_fresh(book: OrderBook, now: float, max_age: float) -> bool:
    """A book is fresh if it was received within ``max_age`` seconds of ``now``."""
    return (now - book.ts_recv) <= max_age
