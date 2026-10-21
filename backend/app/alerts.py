"""Alert engine with per-route cooldown throttling (debounce alert storms)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Alert:
    symbol: str
    buy_venue: str
    sell_venue: str
    net_spread: float
    est_profit: float
    ts: float


class AlertEngine:
    """Emits an alert per opportunity, suppressing repeats within ``cooldown`` seconds."""

    def __init__(self, cooldown: float = 30.0) -> None:
        self.cooldown = cooldown
        self._last: dict[tuple[str, str, str], float] = {}

    def evaluate(self, opportunities: list[dict], now: float) -> list[Alert]:
        alerts: list[Alert] = []
        for opp in opportunities:
            key = (opp["symbol"], opp["buy_venue"], opp["sell_venue"])
            last = self._last.get(key)
            if last is None or (now - last) >= self.cooldown:
                self._last[key] = now
                alerts.append(
                    Alert(
                        symbol=opp["symbol"],
                        buy_venue=opp["buy_venue"],
                        sell_venue=opp["sell_venue"],
                        net_spread=opp["net_spread"],
                        est_profit=opp["est_profit"],
                        ts=now,
                    )
                )
        return alerts

    def reset(self) -> None:
        self._last.clear()
