"""Multi-hop arbitrage detection via Bellman-Ford negative-cycle search.

Generalises the triangular scanner: given a directed graph of conversion rates
between currencies/assets, find a profitable cycle of *any* length. Each edge
``(u -> v)`` with rate ``r`` (units of ``v`` obtained per unit of ``u``) maps to a
weight ``-log(r * (1 - fee))``. A cycle whose weights sum to a negative number is
an arbitrage: the rate product, net of per-leg fees, exceeds 1.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from .triangular import cycle_return


@dataclass(frozen=True)
class ArbitrageCycle:
    """A profitable conversion loop, e.g. ``USD -> EUR -> GBP -> USD``."""

    path: list[str]
    rates: list[float]
    net_return: float


def _best_direction(
    cycle_nodes: list[str],
    rates: Mapping[tuple[str, str], float],
    fee: float,
    min_return: float,
) -> ArbitrageCycle | None:
    """Pick the profitable traversal direction of a recovered cycle."""
    best: ArbitrageCycle | None = None
    for seq in (cycle_nodes, list(reversed(cycle_nodes))):
        pairs = [(seq[i], seq[i + 1]) for i in range(len(seq) - 1)]
        if not pairs or not all(p in rates for p in pairs):
            continue
        leg_rates = [rates[p] for p in pairs]
        net = cycle_return(leg_rates, fee)
        if net > min_return and (best is None or net > best.net_return):
            best = ArbitrageCycle(path=list(seq), rates=leg_rates, net_return=net)
    return best


def find_arbitrage(
    rates: Mapping[tuple[str, str], float],
    fee: float = 0.0,
    min_return: float = 0.0,
) -> ArbitrageCycle | None:
    """Find one profitable conversion cycle, or ``None`` if no arbitrage exists.

    ``rates[(u, v)]`` is the units of ``v`` obtained per unit of ``u``. ``fee`` is
    the proportional cost charged on each leg. Uses Bellman-Ford from a virtual
    source (all distances start at 0) so *any* negative cycle in the graph is
    detected, then walks the predecessor chain to recover the cycle.
    """
    if not rates:
        return None
    if not 0.0 <= fee < 1.0:
        raise ValueError("fee must be in [0, 1)")

    nodes = sorted({c for pair in rates for c in pair})
    edges: list[tuple[str, str, float]] = []
    for (u, v), r in rates.items():
        if r <= 0:
            raise ValueError("conversion rates must be positive")
        edges.append((u, v, -math.log(r * (1.0 - fee))))

    dist = dict.fromkeys(nodes, 0.0)
    pred: dict[str, str | None] = dict.fromkeys(nodes, None)

    updated: str | None = None
    for _ in range(len(nodes)):
        updated = None
        for u, v, w in edges:
            if dist[u] + w < dist[v] - 1e-12:
                dist[v] = dist[u] + w
                pred[v] = u
                updated = v
        if updated is None:
            break
    if updated is None:
        return None  # converged with no negative cycle -> no arbitrage

    # Walk back |V| steps to land strictly inside the cycle, then trace it.
    node: str | None = updated
    for _ in range(len(nodes)):
        node = pred[node]  # type: ignore[index]
    assert node is not None
    cycle_nodes: list[str] = [node]
    cur = pred[node]
    while cur is not None and cur != node:
        cycle_nodes.append(cur)
        cur = pred[cur]
    cycle_nodes.append(node)
    cycle_nodes.reverse()

    return _best_direction(cycle_nodes, rates, fee, min_return)


def find_all_arbitrages(
    rates: Mapping[tuple[str, str], float],
    fee: float = 0.0,
    min_return: float = 0.0,
) -> list[ArbitrageCycle]:
    """Greedily enumerate disjoint arbitrage cycles.

    Finds a cycle, removes its weakest leg, and repeats, so each call surfaces a
    distinct opportunity rather than the same cycle repeatedly.
    """
    remaining = dict(rates)
    found: list[ArbitrageCycle] = []
    for _ in range(len(remaining)):
        cycle = find_arbitrage(remaining, fee, min_return)
        if cycle is None:
            break
        found.append(cycle)
        # Drop the lowest-rate leg to break this cycle and look for others.
        legs = list(zip(cycle.path[:-1], cycle.path[1:]))
        weakest = min(legs, key=lambda p: remaining.get(p, math.inf))
        remaining.pop(weakest, None)
    return found
