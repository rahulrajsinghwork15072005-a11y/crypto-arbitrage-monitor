"""Historical replay: run the detector over a time series of book snapshots.

Replays recorded multi-venue frames through the opportunity detector to measure
how long edges persist, how big they get, and how often a *raw* (gross) spread
fails to survive fees - a practical false-positive rate for naive spread alerts.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from .book import OrderBook
from .detector import DetectorConfig, scan_pairs
from .fees import FeeSchedule
from .spread import raw_spread

__all__ = ["replay"]

Frame = tuple[float, Mapping[str, OrderBook]]


def _has_raw_edge(books: Mapping[str, OrderBook]) -> bool:
    venues = list(books)
    for buy_v in venues:
        for sell_v in venues:
            if buy_v == sell_v:
                continue
            if raw_spread(books[buy_v], books[sell_v]) > 0.0:
                return True
    return False


def replay(
    frames: Sequence[Frame],
    fees: Mapping[str, FeeSchedule],
    config: DetectorConfig = DetectorConfig(),
) -> dict:
    """Replay ``frames`` (``(now, books)``) and summarise opportunity dynamics."""
    n_frames = len(frames)
    opp_frames = 0
    raw_frames = 0
    raw_no_net = 0
    best_nets: list[float] = []
    best_series: list[float] = []
    max_net = 0.0

    active_run: dict[tuple[str, str], int] = {}
    runs: list[int] = []

    for now, books in frames:
        opps = scan_pairs(books, fees, now, config)
        raw_edge = _has_raw_edge(books)
        if raw_edge:
            raw_frames += 1

        if opps:
            opp_frames += 1
            best = max(o.net_spread for o in opps)
            best_nets.append(best)
            best_series.append(best)
            max_net = max(max_net, best)
        else:
            best_series.append(0.0)
            if raw_edge:
                raw_no_net += 1

        pairs_now = {(o.buy_venue, o.sell_venue) for o in opps}
        for pair in list(active_run):
            if pair not in pairs_now:
                runs.append(active_run.pop(pair))
        for pair in pairs_now:
            active_run[pair] = active_run.get(pair, 0) + 1

    runs.extend(active_run.values())

    return {
        "n_frames": n_frames,
        "n_opportunity_frames": opp_frames,
        "n_raw_frames": raw_frames,
        "false_positive_rate": (raw_no_net / raw_frames) if raw_frames else 0.0,
        "avg_best_net_spread": float(np.mean(best_nets)) if best_nets else 0.0,
        "max_net_spread": float(max_net),
        "mean_opportunity_duration": float(np.mean(runs)) if runs else 0.0,
        "best_net_series": best_series,
    }
