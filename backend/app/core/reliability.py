"""Venue reliability scoring from a short history of book snapshots.

Frames market-data quality as infrastructure metrics rather than crypto hype:
how often a venue's book is crossed/invalid, how stale its updates are, and its
transport latency. Produces a 0..1 composite score per venue (higher = better).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

import numpy as np

from .book import OrderBook
from .latency import latency

__all__ = ["VenueReliability", "score_history", "venue_reliability"]


@dataclass(frozen=True)
class VenueReliability:
    venue: str
    n_samples: int
    crossed_rate: float    # fraction of snapshots with best_bid >= best_ask
    stale_rate: float      # fraction of update gaps exceeding max_age
    latency_p95: float     # 95th percentile of ts_recv - ts_exchange
    mean_latency: float
    score: float           # 0..1 composite (higher = more reliable)


def score_history(
    venue: str,
    books: Sequence[OrderBook],
    max_age: float = 2.0,
    latency_ref: float = 0.5,
) -> VenueReliability:
    """Score one venue from its ordered snapshot history."""
    n = len(books)
    if n == 0:
        return VenueReliability(venue, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    latencies = np.array([latency(b.ts_exchange, b.ts_recv) for b in books], dtype=float)
    crossed = np.array([1.0 if b.best_bid >= b.best_ask else 0.0 for b in books])
    recv = np.sort(np.array([b.ts_recv for b in books], dtype=float))
    gaps = np.diff(recv) if n > 1 else np.array([])

    crossed_rate = float(crossed.mean())
    stale_rate = float((gaps > max_age).mean()) if gaps.size else 0.0
    p95 = float(np.percentile(latencies, 95))
    mean_lat = float(latencies.mean())

    score = 1.0 - 0.5 * crossed_rate - 0.3 * stale_rate - 0.2 * min(p95 / latency_ref, 1.0)
    score = float(max(0.0, min(1.0, score)))
    return VenueReliability(venue, n, crossed_rate, stale_rate, p95, mean_lat, score)


def venue_reliability(
    history: Mapping[str, Sequence[OrderBook]],
    max_age: float = 2.0,
    latency_ref: float = 0.5,
) -> list[dict]:
    """Score every venue in ``history`` (venue -> ordered snapshots)."""
    return [
        asdict(score_history(venue, books, max_age, latency_ref))
        for venue, books in history.items()
    ]
