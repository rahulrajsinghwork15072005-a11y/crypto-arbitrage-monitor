import pytest

from app.core.book import Level, OrderBook
from app.core.liquidity import is_fresh, passes_liquidity
from app.core.spread import raw_spread


def book(venue, bid, ask, size=1.0, ts_recv=0.0):
    return OrderBook(
        venue, "BTC-USD",
        bids=[Level(bid, size)], asks=[Level(ask, size)],
        ts_exchange=ts_recv, ts_recv=ts_recv,
    )


def test_raw_spread():
    buy = book("A", 99.9, 100.0)
    sell = book("B", 101.0, 101.1)
    assert raw_spread(buy, sell) == pytest.approx((101.0 - 100.0) / 100.0)


def test_passes_liquidity():
    b = book("A", 100, 101, size=2.0)
    assert passes_liquidity(b, min_qty=1.5, top_levels=1)
    assert not passes_liquidity(b, min_qty=3.0, top_levels=1)


def test_freshness():
    b = book("A", 100, 101, ts_recv=1000.0)
    assert is_fresh(b, now=1001.0, max_age=2.0)
    assert not is_fresh(b, now=1005.0, max_age=2.0)
