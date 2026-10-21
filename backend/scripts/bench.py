"""Micro-benchmarks for the arbitrage monitor.

Times the Bellman-Ford multi-hop arbitrage search over conversion graphs of
growing size and the pairwise cross-venue detector. Runs entirely offline.

    python scripts/bench.py            # from backend/

Numbers are wall-clock and machine-dependent; treat them as relative signals.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from app.core.arbitrage_graph import find_arbitrage  # noqa: E402
from app.core.detector import DetectorConfig, scan_pairs  # noqa: E402
from app.data.synthetic import build_books, fee_table  # noqa: E402


def _best(fn, repeats: int) -> float:
    best = float("inf")
    for _ in range(max(1, repeats)):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best


def _complete_graph(n: int, seed: int = 0) -> dict[tuple[str, str], float]:
    """A complete conversion graph with one perturbed edge (an arbitrage)."""
    rng = np.random.default_rng(seed)
    values = {f"C{i}": float(rng.uniform(0.5, 2.0)) for i in range(n)}
    ccy = list(values)
    rates = {(a, b): values[a] / values[b] for a in ccy for b in ccy if a != b}
    rates[(ccy[0], ccy[1])] *= 1.05
    return rates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark the arbitrage monitor.")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args(argv)

    print("\nArbitrage monitor benchmarks")
    print("-" * 58)
    print(f"  {'graph':18} {'edges':>7} {'ms / search':>12} {'searches/s':>12}")
    for n in (5, 10, 20, 40):
        rates = _complete_graph(n)
        secs = _best(lambda r=rates: find_arbitrage(r, fee=0.0005), args.repeats)
        print(f"  Bellman-Ford ({n:2d})   {len(rates):>7} {secs * 1e3:>12.3f} {1.0 / secs:>12,.0f}")

    now = time.time()
    books = build_books(now=now)
    scan = _best(
        lambda: scan_pairs(books, fee_table(), now, DetectorConfig(threshold=0.0005)),
        args.repeats,
    )
    print(f"\n  cross-venue detector  {scan * 1e3:8.3f} ms  ({len(books)} venues)")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
