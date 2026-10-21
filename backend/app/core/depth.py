"""Depth-aware fills, slippage, and maximum executable size."""
from __future__ import annotations

import math

from .book import Level
from .fees import FeeSchedule, net_spread


def fill_buy(asks: list[Level], qty: float) -> tuple[float, float]:
    """Walk the ask side to buy ``qty``. Returns ``(filled_qty, vwap)``."""
    remaining, cost, filled = qty, 0.0, 0.0
    for level in asks:
        take = min(level.size, remaining)
        cost += take * level.price
        filled += take
        remaining -= take
        if remaining <= 1e-12:
            break
    vwap = cost / filled if filled > 0 else math.nan
    return filled, vwap


def fill_sell(bids: list[Level], qty: float) -> tuple[float, float]:
    """Walk the bid side to sell ``qty``. Returns ``(filled_qty, vwap)``."""
    remaining, proceeds, filled = qty, 0.0, 0.0
    for level in bids:
        take = min(level.size, remaining)
        proceeds += take * level.price
        filled += take
        remaining -= take
        if remaining <= 1e-12:
            break
    vwap = proceeds / filled if filled > 0 else math.nan
    return filled, vwap


def slippage(best_price: float, vwap: float) -> float:
    """Fractional slippage of a VWAP fill versus the best price."""
    if best_price <= 0:
        return math.nan
    return (vwap - best_price) / best_price


def net_spread_for_size(
    buy_asks: list[Level],
    sell_bids: list[Level],
    qty: float,
    fee_buy: FeeSchedule,
    fee_sell: FeeSchedule,
) -> float:
    """Fee-adjusted net spread achievable for ``qty`` (``-inf`` if unfillable)."""
    fb, buy_vwap = fill_buy(buy_asks, qty)
    fs, sell_vwap = fill_sell(sell_bids, qty)
    if fb + 1e-9 < qty or fs + 1e-9 < qty:
        return float("-inf")
    return net_spread(buy_vwap, sell_vwap, fee_buy, fee_sell)


def max_executable_size(
    buy_asks: list[Level],
    sell_bids: list[Level],
    fee_buy: FeeSchedule,
    fee_sell: FeeSchedule,
    threshold: float,
    qty_cap: float | None = None,
    iterations: int = 60,
) -> float:
    """Largest size whose net spread still exceeds ``threshold``.

    Net spread is monotonically non-increasing in size (deeper fills are worse),
    so we bisect on the threshold crossing.
    """
    q_max = min(
        sum(level.size for level in buy_asks),
        sum(level.size for level in sell_bids),
    )
    if qty_cap is not None:
        q_max = min(q_max, qty_cap)
    if q_max <= 0:
        return 0.0

    probe = min(q_max, 1e-9)
    if net_spread_for_size(buy_asks, sell_bids, probe, fee_buy, fee_sell) <= threshold:
        return 0.0
    if net_spread_for_size(buy_asks, sell_bids, q_max, fee_buy, fee_sell) > threshold:
        return float(q_max)

    lo, hi = 0.0, q_max
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if net_spread_for_size(buy_asks, sell_bids, mid, fee_buy, fee_sell) > threshold:
            lo = mid
        else:
            hi = mid
    return float(lo)
