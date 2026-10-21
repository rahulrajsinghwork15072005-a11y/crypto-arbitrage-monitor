"""Triangular (single-venue) arbitrage scanning."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


def cycle_return(rates: Sequence[float], fee: float = 0.0) -> float:
    """Net return of a multi-leg conversion cycle.

    ``rates[i]`` is the units of the next currency obtained per unit of the
    current currency on leg ``i`` (already direction-adjusted). A profitable
    cycle has a positive return.
    """
    product = 1.0
    for r in rates:
        if r <= 0:
            raise ValueError("conversion rates must be positive")
        product *= r
    product *= (1.0 - fee) ** len(rates)
    return product - 1.0


@dataclass(frozen=True)
class TriangularOpportunity:
    venue: str
    legs: list[str]
    rates: list[float]
    net_return: float


def scan_triangle(
    venue: str,
    legs: list[str],
    rates: Sequence[float],
    fee: float = 0.0,
    threshold: float = 0.0,
) -> TriangularOpportunity | None:
    """Return an opportunity if the cycle clears ``threshold`` after fees."""
    ret = cycle_return(rates, fee)
    if ret <= threshold:
        return None
    return TriangularOpportunity(venue=venue, legs=legs, rates=list(rates), net_return=ret)
