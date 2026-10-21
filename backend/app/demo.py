"""Demo orchestration for the arbitrage monitor (synthetic feed)."""
from __future__ import annotations

import time
from dataclasses import asdict

import numpy as np

from .core.arbitrage_graph import find_all_arbitrages
from .core.book import OrderBook
from .core.detector import DetectorConfig, scan_pairs
from .core.latency import latency_stats
from .core.reliability import venue_reliability
from .core.replay import replay
from .core.triangular import cycle_return, scan_triangle
from .data.synthetic import (
    build_books,
    fee_table,
    latency_samples,
    opportunity_history,
    triangle_rates,
)

_THRESHOLD = 0.0005


def book_to_dict(b: OrderBook) -> dict:
    return {
        "venue": b.venue,
        "symbol": b.symbol,
        "bids": [[lvl.price, lvl.size] for lvl in b.bids],
        "asks": [[lvl.price, lvl.size] for lvl in b.asks],
        "best_bid": b.best_bid,
        "best_ask": b.best_ask,
        "mid": b.mid,
        "ts_exchange": b.ts_exchange,
        "ts_recv": b.ts_recv,
    }


def demo_books() -> dict:
    now = time.time()
    books = build_books(now=now)
    return {"now": now, "books": {v: book_to_dict(b) for v, b in books.items()}}


def demo_opportunities() -> dict:
    now = time.time()
    books = build_books(now=now)
    opps = scan_pairs(books, fee_table(), now, DetectorConfig(threshold=_THRESHOLD))
    return {"now": now, "threshold": _THRESHOLD, "opportunities": [asdict(o) for o in opps]}


def demo_triangular(profitable: bool = True) -> dict:
    legs, rates = triangle_rates(profitable)
    fee = 0.001
    ret = cycle_return(rates, fee=fee)
    opp = scan_triangle("BINANCE", legs, rates, fee=fee, threshold=0.0)
    return {
        "legs": legs,
        "rates": rates,
        "fee": fee,
        "net_return": ret,
        "is_opportunity": opp is not None,
    }


def demo_history() -> dict:
    hist = opportunity_history()
    t = np.asarray(hist["t"], dtype=float)
    s = np.asarray(hist["net_spread"], dtype=float)

    mask = s > 1e-5
    if mask.sum() >= 2:
        slope, intercept = np.polyfit(t[mask], np.log(s[mask]), 1)
        decay_rate = float(-slope)
        s0 = float(np.exp(intercept))
        half_life = float(np.log(2) / decay_rate) if decay_rate > 0 else float("inf")
    else:
        decay_rate, s0, half_life = 0.0, float(s[0]), float("inf")

    below = np.where(s < _THRESHOLD)[0]
    lifetime = float(t[below[0]]) if below.size else float(t[-1])

    return {
        "t": hist["t"],
        "net_spread": hist["net_spread"],
        "threshold": _THRESHOLD,
        "decay_rate": decay_rate,
        "s0": s0,
        "half_life": half_life,
        "lifetime": lifetime,
    }


def demo_latency() -> dict:
    samples = latency_samples()
    return {v: latency_stats(s) for v, s in samples.items()}


def demo_reliability(n_frames: int = 20) -> dict:
    """Score venue market-data reliability over a synthetic snapshot history."""
    base = time.time()
    dt = 0.5
    history: dict[str, list[OrderBook]] = {}
    for i in range(n_frames):
        books = build_books(now=base + i * dt, seed=i)
        for venue, book in books.items():
            history.setdefault(venue, []).append(book)
    return {
        "now": base + n_frames * dt,
        "n_frames": n_frames,
        "venues": venue_reliability(history),
    }


def demo_replay(n_frames: int = 40) -> dict:
    """Replay a synthetic frame series through the detector for opportunity dynamics."""
    base = time.time()
    dt = 0.5
    frames = []
    for i in range(n_frames):
        now_i = base + i * dt
        books = build_books(now=now_i, seed=i, with_arb=(i % 4 != 0))
        frames.append((now_i, books))
    return replay(frames, fee_table(), DetectorConfig(threshold=_THRESHOLD))


def demo_arbitrage_graph(profitable: bool = True) -> dict:
    """Multi-hop (Bellman-Ford) arbitrage over a small FX-style conversion graph.

    The graph is built from consistent reference values, so every cycle product is
    exactly 1 (no arbitrage) until a single rate is perturbed when ``profitable``.
    """
    values = {"USD": 1.0, "EUR": 1.10, "GBP": 1.27, "JPY": 1.0 / 150.0}  # USD per unit
    pairs = [
        ("USD", "EUR"), ("EUR", "USD"), ("EUR", "GBP"), ("GBP", "EUR"),
        ("GBP", "USD"), ("USD", "GBP"), ("USD", "JPY"), ("JPY", "USD"),
        ("EUR", "JPY"), ("JPY", "EUR"),
    ]
    rates = {(a, b): values[a] / values[b] for a, b in pairs}
    if profitable:
        rates[("EUR", "GBP")] *= 1.02  # a ~2% mispricing opens an arbitrage loop
    fee = 0.0005
    cycles = find_all_arbitrages(rates, fee=fee, min_return=0.0)
    return {
        "fee": fee,
        "profitable": profitable,
        "rates": [{"from": a, "to": b, "rate": r} for (a, b), r in rates.items()],
        "cycles": [{"path": c.path, "rates": c.rates, "net_return": c.net_return} for c in cycles],
        "n_cycles": len(cycles),
    }
