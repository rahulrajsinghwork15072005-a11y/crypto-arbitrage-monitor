"""Fee model and fee-adjusted profitability."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeeSchedule:
    """Per-venue costs.

    ``taker`` is a fraction (e.g. 0.001 = 10 bps). ``withdrawal`` is a per-unit
    transfer cost expressed in quote currency (0 to ignore).
    """

    taker: float = 0.001
    withdrawal: float = 0.0


def net_profit_per_unit(
    buy_price: float,
    sell_price: float,
    fee_buy: FeeSchedule,
    fee_sell: FeeSchedule,
) -> float:
    """Profit per unit of base from buying at ``buy_price`` and selling at ``sell_price``."""
    proceeds = sell_price * (1.0 - fee_sell.taker)
    cost = buy_price * (1.0 + fee_buy.taker)
    return proceeds - cost - fee_sell.withdrawal


def net_spread(
    buy_price: float,
    sell_price: float,
    fee_buy: FeeSchedule,
    fee_sell: FeeSchedule,
) -> float:
    """Fee-adjusted net spread as a fraction of the (fee-inclusive) cost basis."""
    cost = buy_price * (1.0 + fee_buy.taker)
    if cost <= 0:
        return float("-inf")
    return net_profit_per_unit(buy_price, sell_price, fee_buy, fee_sell) / cost
