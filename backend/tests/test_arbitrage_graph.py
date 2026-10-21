"""Tests for Bellman-Ford multi-hop arbitrage detection."""
import pytest
from fastapi.testclient import TestClient

from app.core.arbitrage_graph import find_all_arbitrages, find_arbitrage
from app.main import app

client = TestClient(app)


def _consistent_rates() -> dict[tuple[str, str], float]:
    """A no-arbitrage graph: every cycle product is exactly 1."""
    values = {"USD": 1.0, "EUR": 1.10, "GBP": 1.27, "JPY": 1.0 / 150.0}
    pairs = [
        ("USD", "EUR"), ("EUR", "USD"), ("EUR", "GBP"), ("GBP", "EUR"),
        ("GBP", "USD"), ("USD", "GBP"), ("USD", "JPY"), ("JPY", "USD"),
    ]
    return {(a, b): values[a] / values[b] for a, b in pairs}


def test_no_arbitrage_in_consistent_graph():
    assert find_arbitrage(_consistent_rates(), fee=0.0) is None


def test_detects_triangular_arbitrage():
    rates = _consistent_rates()
    rates[("EUR", "GBP")] *= 1.05  # introduce a 5% mispricing
    cyc = find_arbitrage(rates, fee=0.0)
    assert cyc is not None
    assert cyc.net_return > 0
    product = 1.0
    for r in cyc.rates:
        product *= r
    assert product - 1.0 == pytest.approx(cyc.net_return, abs=1e-9)
    assert cyc.path[0] == cyc.path[-1]  # closed loop


def test_arbitrage_disappears_under_fees():
    rates = _consistent_rates()
    rates[("EUR", "GBP")] *= 1.005  # a tiny 0.5% edge
    assert find_arbitrage(rates, fee=0.0) is not None
    assert find_arbitrage(rates, fee=0.01) is None  # 1%/leg fee erases it


def test_four_hop_cycle_found():
    rates = {("A", "B"): 2.0, ("B", "C"): 2.0, ("C", "D"): 2.0, ("D", "A"): 0.2}
    cyc = find_arbitrage(rates, fee=0.0)  # product 1.6 > 1
    assert cyc is not None
    assert len(cyc.path) == 5  # A->B->C->D->A
    assert cyc.net_return == pytest.approx(0.6, abs=1e-9)


def test_find_all_returns_cycles():
    rates = _consistent_rates()
    rates[("EUR", "GBP")] *= 1.05
    cycles = find_all_arbitrages(rates, fee=0.0)
    assert len(cycles) >= 1
    assert all(c.net_return > 0 for c in cycles)


def test_invalid_rate_raises():
    with pytest.raises(ValueError):
        find_arbitrage({("A", "B"): -1.0, ("B", "A"): 1.0})


def test_api_demo_arbitrage_graph():
    resp = client.get("/api/demo/arbitrage-graph", params={"profitable": True})
    assert resp.status_code == 200
    assert resp.json()["n_cycles"] >= 1
    resp2 = client.get("/api/demo/arbitrage-graph", params={"profitable": False})
    assert resp2.json()["n_cycles"] == 0


def test_api_post_arbitrage_graph():
    body = {
        "rates": [
            {"from": "A", "to": "B", "rate": 2.0},
            {"from": "B", "to": "C", "rate": 2.0},
            {"from": "C", "to": "A", "rate": 0.3},
        ],
        "fee": 0.0,
    }
    resp = client.post("/api/arbitrage/graph", json=body)
    assert resp.status_code == 200
    assert resp.json()["n_cycles"] >= 1
