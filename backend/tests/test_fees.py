from app.core.fees import FeeSchedule, net_profit_per_unit, net_spread


def test_equal_prices_with_fees_is_unprofitable():
    f = FeeSchedule(taker=0.001)
    assert net_profit_per_unit(100, 100, f, f) < 0
    assert net_spread(100, 100, f, f) < 0


def test_clear_spread_is_profitable():
    f = FeeSchedule(taker=0.001)
    assert net_profit_per_unit(100, 101, f, f) > 0
    assert net_spread(100, 101, f, f) > 0


def test_withdrawal_cost_reduces_profit():
    f0 = FeeSchedule(taker=0.001, withdrawal=0.0)
    f1 = FeeSchedule(taker=0.001, withdrawal=0.5)
    assert net_profit_per_unit(100, 101, f0, f1) < net_profit_per_unit(100, 101, f0, f0)
