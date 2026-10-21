import pytest

from app.core.triangular import cycle_return, scan_triangle


def test_consistent_cycle_is_flat():
    assert cycle_return([2.0, 0.5]) == pytest.approx(0.0)


def test_profitable_cycle_positive():
    assert cycle_return([2.0, 0.51]) > 0


def test_fees_reduce_return():
    assert cycle_return([2.0, 0.51], fee=0.01) < cycle_return([2.0, 0.51], fee=0.0)


def test_nonpositive_rate_raises():
    with pytest.raises(ValueError):
        cycle_return([1.0, -2.0])


def test_scan_triangle_threshold():
    assert scan_triangle("V", ["a->b", "b->a"], [2.0, 0.5], threshold=0.0) is None
    opp = scan_triangle("V", ["a->b", "b->a"], [2.0, 0.6], threshold=0.0)
    assert opp is not None
    assert opp.net_return > 0
