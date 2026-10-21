"""Latency and staleness metrics."""
from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def latency(ts_exchange: float, ts_recv: float) -> float:
    """Transport latency: time between exchange stamp and local receipt."""
    return ts_recv - ts_exchange


def age(now: float, ts_recv: float) -> float:
    """How stale a book is relative to ``now``."""
    return now - ts_recv


def latency_stats(samples: ArrayLike) -> dict[str, float]:
    """Summary statistics for a sample of latency measurements."""
    arr = np.asarray(samples, dtype=float)
    if arr.size == 0:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0, "n": 0}
    return {
        "mean": float(arr.mean()),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(arr.max()),
        "n": int(arr.size),
    }
