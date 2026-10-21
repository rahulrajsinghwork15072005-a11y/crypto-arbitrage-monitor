"""Opportunity detector: scans venue pairs for fee/slippage-adjusted edges."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .book import OrderBook
from .depth import fill_buy, fill_sell, max_executable_size, slippage
from .fees import FeeSchedule, net_profit_per_unit, net_spread
from .liquidity import is_fresh, passes_liquidity
from .spread import raw_spread


@dataclass(frozen=True)
class Opportunity:
    symbol: str
    buy_venue: str
    sell_venue: str
    buy_price: float
    sell_price: float
    gross_spread: float
    net_spread: float
    max_size: float
    est_profit: float
    buy_slippage: float
    sell_slippage: float
    ts: float


@dataclass
class DetectorConfig:
    threshold: float = 0.0005      # 5 bps minimum net edge
    min_qty: float = 0.05
    top_levels: int = 5
    max_age: float = 2.0           # seconds
    qty_cap: float | None = None


def scan_pairs(
    books: Mapping[str, OrderBook],
    fees: Mapping[str, FeeSchedule],
    now: float,
    config: DetectorConfig = DetectorConfig(),
) -> list[Opportunity]:
    """Find all directed (buy A, sell B) opportunities passing every filter."""
    opportunities: list[Opportunity] = []
    venues = list(books)

    for buy_v in venues:
        for sell_v in venues:
            if buy_v == sell_v:
                continue
            buy_book = books[buy_v]
            sell_book = books[sell_v]

            if not (is_fresh(buy_book, now, config.max_age) and is_fresh(sell_book, now, config.max_age)):
                continue

            fee_buy = fees.get(buy_v, FeeSchedule())
            fee_sell = fees.get(sell_v, FeeSchedule())

            net0 = net_spread(buy_book.best_ask, sell_book.best_bid, fee_buy, fee_sell)
            if net0 <= config.threshold:
                continue

            if not (
                passes_liquidity(buy_book, config.min_qty, config.top_levels)
                and passes_liquidity(sell_book, config.min_qty, config.top_levels)
            ):
                continue

            size = max_executable_size(
                buy_book.asks, sell_book.bids, fee_buy, fee_sell,
                threshold=config.threshold, qty_cap=config.qty_cap,
            )
            if size <= 0:
                continue

            _, buy_vwap = fill_buy(buy_book.asks, size)
            _, sell_vwap = fill_sell(sell_book.bids, size)
            profit = net_profit_per_unit(buy_vwap, sell_vwap, fee_buy, fee_sell) * size

            opportunities.append(
                Opportunity(
                    symbol=buy_book.symbol,
                    buy_venue=buy_v,
                    sell_venue=sell_v,
                    buy_price=buy_book.best_ask,
                    sell_price=sell_book.best_bid,
                    gross_spread=raw_spread(buy_book, sell_book),
                    net_spread=net_spread(buy_vwap, sell_vwap, fee_buy, fee_sell),
                    max_size=size,
                    est_profit=profit,
                    buy_slippage=slippage(buy_book.best_ask, buy_vwap),
                    sell_slippage=slippage(sell_book.best_bid, sell_vwap),
                    ts=now,
                )
            )

    opportunities.sort(key=lambda o: o.net_spread, reverse=True)
    return opportunities
