"""Synthetic multi-venue data: order books, fees, triangles, history, latency."""
from __future__ import annotations

import time

import numpy as np

from ..core.book import Level, OrderBook
from ..core.fees import FeeSchedule

VENUES = ["BINANCE", "COINBASE", "KRAKEN"]


def fee_table() -> dict[str, FeeSchedule]:
    return {
        "BINANCE": FeeSchedule(taker=0.0010, withdrawal=0.0),
        "COINBASE": FeeSchedule(taker=0.0010, withdrawal=0.0),
        "KRAKEN": FeeSchedule(taker=0.0010, withdrawal=0.0),
    }


def build_books(
    symbol: str = "BTC-USD",
    ref: float = 50_000.0,
    now: float | None = None,
    seed: int = 0,
    with_arb: bool = True,
) -> dict[str, OrderBook]:
    """Construct normalized books for each venue around a reference price.

    When ``with_arb`` is true one venue is priced low enough that a fee-adjusted
    cross-venue edge exists; otherwise venue prices cluster and no edge survives.
    """
    rng = np.random.default_rng(seed)
    now = time.time() if now is None else now

    # per-venue mid offset in basis points
    offsets = {"BINANCE": 0.0, "COINBASE": -40.0 if with_arb else 5.0, "KRAKEN": 8.0}
    books: dict[str, OrderBook] = {}

    for venue in VENUES:
        mid = ref * (1.0 + offsets[venue] / 1e4)
        half_spread = mid * float(rng.uniform(1.0, 2.5)) / 1e4
        best_bid = mid - half_spread
        best_ask = mid + half_spread
        step = mid * 1e-4

        bids = [
            Level(round(best_bid - i * step, 2), round(float(rng.uniform(0.3, 1.5)) * (1 + 0.2 * i), 4))
            for i in range(8)
        ]
        asks = [
            Level(round(best_ask + i * step, 2), round(float(rng.uniform(0.3, 1.5)) * (1 + 0.2 * i), 4))
            for i in range(8)
        ]
        books[venue] = OrderBook(
            venue=venue,
            symbol=symbol,
            bids=bids,
            asks=asks,
            ts_exchange=now - float(rng.uniform(0.02, 0.15)),
            ts_recv=now - float(rng.uniform(0.0, 0.05)),
        )
    return books


def triangle_rates(profitable: bool = True) -> tuple[list[str], list[float]]:
    """A direction-adjusted USD→BTC→ETH→USD cycle (consistent set has product 1)."""
    legs = ["USD->BTC", "BTC->ETH", "ETH->USD"]
    rates = [1.0 / 50_000.0, 50_000.0 / 3_000.0, 3_000.0]
    if profitable:
        rates[1] *= 1.012
    return legs, rates


def opportunity_history(
    seed: int = 0, n: int = 40, dt: float = 0.5, s0: float = 0.004, lam: float = 0.15
) -> dict[str, list[float]]:
    """A decaying net-spread series representing an edge closing over time."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) * dt
    spread = s0 * np.exp(-lam * t) + rng.normal(0.0, 1e-4, n)
    return {"t": t.tolist(), "net_spread": spread.tolist()}


def latency_samples(seed: int = 0, n: int = 200) -> dict[str, list[float]]:
    rng = np.random.default_rng(seed)
    base = {"BINANCE": 0.0, "COINBASE": 0.01, "KRAKEN": 0.03}
    return {v: (rng.uniform(0.02, 0.05, n) + base[v]).tolist() for v in VENUES}
