import pytest

from app.core.book import Level, OrderBook


def make_book():
    return OrderBook(
        "X", "BTC-USD",
        bids=[Level(100, 1), Level(99, 2)],
        asks=[Level(101, 1), Level(102, 2)],
        ts_exchange=0.0, ts_recv=0.0,
    )


def test_best_prices_and_mid():
    b = make_book()
    assert b.best_bid == 100
    assert b.best_ask == 101
    assert b.mid == 100.5
    assert b.spread == 1


def test_depth():
    b = make_book()
    assert b.depth("bid", 2) == 3
    assert b.depth("ask", 1) == 1


def test_empty_side_rejected():
    with pytest.raises(ValueError):
        OrderBook("X", "S", bids=[], asks=[Level(1, 1)], ts_exchange=0, ts_recv=0)
