"""Live exchange order books via ccxt, with a graceful offline fallback.

Returns ``None`` (per venue) when ccxt is missing or the network is unavailable,
so callers can fall back to the synthetic feed and the test suite stays offline.
"""
from __future__ import annotations

import time

from ..core.book import Level, OrderBook

try:  # optional dependency
    import ccxt as _ccxt

    _HAS_CCXT = True
except Exception:  # pragma: no cover - import guard
    _HAS_CCXT = False

_VENUE_TO_CCXT = {"BINANCE": "binance", "COINBASE": "coinbase", "KRAKEN": "kraken"}


def fetch_order_book(
    venue: str, symbol: str = "BTC/USDT", limit: int = 10, allow_network: bool = True
) -> OrderBook | None:
    if not (allow_network and _HAS_CCXT):
        return None
    exchange_id = _VENUE_TO_CCXT.get(venue, venue.lower())
    try:  # pragma: no cover - network path
        exchange = getattr(_ccxt, exchange_id)()
        ob = exchange.fetch_order_book(symbol, limit)
        if not ob.get("bids") or not ob.get("asks"):
            return None
        now = time.time()
        ts_exchange = (ob.get("timestamp") or now * 1000) / 1000.0
        bids = [Level(float(p), float(s)) for p, s in ob["bids"][:limit]]
        asks = [Level(float(p), float(s)) for p, s in ob["asks"][:limit]]
        return OrderBook(venue, symbol, bids, asks, ts_exchange=ts_exchange, ts_recv=now)
    except Exception:  # pragma: no cover - network/parse failures
        return None


def fetch_books(
    venues: list[str], symbol: str = "BTC/USDT", allow_network: bool = True
) -> tuple[dict[str, OrderBook], str]:
    """Fetch books for several venues. Returns ``(books, source)``."""
    books: dict[str, OrderBook] = {}
    for venue in venues:
        book = fetch_order_book(venue, symbol, allow_network=allow_network)
        if book is not None:
            books[venue] = book
    return books, ("ccxt" if books else "unavailable")
