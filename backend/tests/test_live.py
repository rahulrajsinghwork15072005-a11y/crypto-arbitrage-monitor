from app.data.live_feed import fetch_books
from app.live import live_opportunities


def test_fetch_books_offline_is_empty():
    books, source = fetch_books(["BINANCE", "COINBASE"], allow_network=False)
    assert books == {}
    assert source == "unavailable"


def test_live_opportunities_offline_note():
    out = live_opportunities(allow_network=False)
    assert out["source"] == "unavailable"
    assert out["opportunities"] == []
    assert "note" in out
