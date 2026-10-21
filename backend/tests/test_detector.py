from app.core.detector import DetectorConfig, scan_pairs
from app.data.synthetic import build_books, fee_table


def test_detects_cross_venue_arbitrage():
    now = 1000.0
    books = build_books(now=now, seed=1, with_arb=True)
    opps = scan_pairs(books, fee_table(), now, DetectorConfig())
    assert len(opps) >= 1
    top = opps[0]
    assert top.buy_venue == "COINBASE"  # the under-priced venue
    assert top.net_spread > 0
    assert top.max_size > 0
    assert top.est_profit > 0


def test_no_false_positive_without_arb():
    now = 1000.0
    books = build_books(now=now, seed=1, with_arb=False)
    assert scan_pairs(books, fee_table(), now, DetectorConfig()) == []


def test_stale_books_excluded():
    now = 1000.0
    books = build_books(now=now, seed=1, with_arb=True)
    # scan far in the future -> every book is stale -> no opportunities
    opps = scan_pairs(books, fee_table(), now + 10.0, DetectorConfig(max_age=2.0))
    assert opps == []
