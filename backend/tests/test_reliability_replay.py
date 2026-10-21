"""Tests for venue reliability scoring and the historical replay analyzer."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.book import Level, OrderBook
from app.core.detector import DetectorConfig
from app.core.reliability import score_history
from app.core.replay import replay
from app.data.synthetic import fee_table
from app.main import app

client = TestClient(app)


def _book(venue, bid, ask, ts_exchange, ts_recv, size=1.0):
    return OrderBook(
        venue=venue,
        symbol="BTC-USD",
        bids=[Level(bid, size)],
        asks=[Level(ask, size)],
        ts_exchange=ts_exchange,
        ts_recv=ts_recv,
    )


def test_clean_venue_scores_higher_than_bad():
    clean = [_book("CLEAN", 100.0, 101.0, ts_exchange=i - 0.05, ts_recv=i) for i in range(5)]
    # Crossed books (bid >= ask), high latency, and large update gaps.
    bad = [_book("BAD", 101.0, 100.0, ts_exchange=3 * i - 0.6, ts_recv=3 * i) for i in range(5)]

    c = score_history("CLEAN", clean)
    b = score_history("BAD", bad)
    assert c.score > b.score
    assert b.crossed_rate == 1.0
    assert b.stale_rate > 0.0
    assert c.crossed_rate == 0.0


def test_empty_history_scores_zero():
    r = score_history("X", [])
    assert r.n_samples == 0 and r.score == 0.0


def _frame(now, a_ask, b_bid):
    books = {
        "A": _book("A", a_ask - 1.0, a_ask, now - 0.01, now),
        "B": _book("B", b_bid, b_bid + 1.0, now - 0.01, now),
    }
    return (now, books)


def test_replay_opportunity_dynamics():
    fees = fee_table()
    cfg = DetectorConfig(threshold=0.0005)
    frames = [
        _frame(0.0, 100.0, 102.0),   # buy A@100, sell B@102 -> net opportunity
        _frame(1.0, 100.0, 102.0),   # ... persists
        _frame(2.0, 100.0, 102.0),   # ... 3 frames -> duration 3
        _frame(3.0, 100.0, 99.0),    # no edge at all
        _frame(4.0, 100.0, 99.0),    # no edge
        _frame(5.0, 100.0, 100.1),   # raw +0.1% edge but fees kill it (false positive)
    ]
    stats = replay(frames, fees, cfg)
    assert stats["n_frames"] == 6
    assert stats["n_opportunity_frames"] == 3
    assert stats["mean_opportunity_duration"] == pytest.approx(3.0)
    assert stats["max_net_spread"] > 0.0
    # raw edge in the 3 opp frames + 1 false-positive frame; only the latter lacks net.
    assert stats["false_positive_rate"] == pytest.approx(0.25)
    assert len(stats["best_net_series"]) == 6


def test_reliability_endpoint():
    body = client.get("/api/demo/reliability?n_frames=12").json()
    assert len(body["venues"]) == 3
    for v in body["venues"]:
        assert 0.0 <= v["score"] <= 1.0


def test_replay_endpoint():
    body = client.get("/api/demo/replay?n_frames=24").json()
    assert body["n_frames"] == 24
    assert "false_positive_rate" in body
    assert "mean_opportunity_duration" in body
