"""Live-data orchestration for the arbitrage monitor."""
from __future__ import annotations

import time
from dataclasses import asdict

from .core.detector import DetectorConfig, scan_pairs
from .core.fees import FeeSchedule
from .data.live_feed import fetch_books

_VENUES = ["BINANCE", "COINBASE", "KRAKEN"]


def live_opportunities(symbol: str = "BTC/USDT", allow_network: bool = True) -> dict:
    books, source = fetch_books(_VENUES, symbol, allow_network=allow_network)
    if not books:
        return {
            "symbol": symbol,
            "source": "unavailable",
            "note": "live feed unavailable (offline or ccxt missing); "
            "use /api/demo/opportunities for the synthetic feed",
            "opportunities": [],
        }
    now = time.time()
    fees = {v: FeeSchedule(taker=0.001) for v in books}
    opps = scan_pairs(books, fees, now, DetectorConfig(threshold=0.0005, max_age=10.0))
    return {
        "symbol": symbol,
        "source": source,
        "venues": list(books),
        "books": {
            v: {"best_bid": b.best_bid, "best_ask": b.best_ask, "mid": b.mid}
            for v, b in books.items()
        },
        "opportunities": [asdict(o) for o in opps],
    }
