"""Raw cross-venue spread (before fees)."""
from __future__ import annotations

from .book import OrderBook


def raw_spread(buy_book: OrderBook, sell_book: OrderBook) -> float:
    """Top-of-book gross spread: buy at ``buy_book`` ask, sell at ``sell_book`` bid."""
    buy_px = buy_book.best_ask
    sell_px = sell_book.best_bid
    if buy_px <= 0:
        return float("-inf")
    return (sell_px - buy_px) / buy_px
