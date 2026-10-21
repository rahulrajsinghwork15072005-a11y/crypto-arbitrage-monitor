
import pytest

from app.core.book import Level
from app.core.depth import (
    fill_buy,
    fill_sell,
    max_executable_size,
    net_spread_for_size,
    slippage,
)
from app.core.fees import FeeSchedule


def test_fill_buy_vwap():
    asks = [Level(101, 1), Level(102, 2), Level(103, 5)]
    assert fill_buy(asks, 1) == (1, 101)
    assert fill_buy(asks, 2) == (2, 101.5)
    filled, vwap = fill_buy(asks, 4)
    assert filled == 4
    assert vwap == pytest.approx(102.0)  # (101 + 102*2 + 103) / 4


def test_fill_sell_vwap():
    bids = [Level(100, 1), Level(99, 2)]
    assert fill_sell(bids, 2) == (2, 99.5)


def test_slippage():
    assert slippage(101, 102) == pytest.approx(1 / 101)


def test_net_spread_for_size_unfillable():
    asks = [Level(101, 1)]
    bids = [Level(105, 1)]
    f = FeeSchedule(taker=0.0)
    assert net_spread_for_size(asks, bids, 10, f, f) == float("-inf")


def test_max_executable_size_monotonic_in_threshold():
    asks = [Level(100, 5)]
    bids = [Level(101, 5)]
    f = FeeSchedule(taker=0.0)
    big = max_executable_size(asks, bids, f, f, threshold=0.001)
    small = max_executable_size(asks, bids, f, f, threshold=0.005)
    assert big >= small
    assert big <= 5  # capped by available depth
