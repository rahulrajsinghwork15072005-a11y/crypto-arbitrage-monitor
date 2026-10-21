"""Bounded in-memory opportunity history with simple aggregate stats."""
from __future__ import annotations

from collections import deque


class OpportunityHistory:
    def __init__(self, capacity: int = 1000) -> None:
        self._items: deque[dict] = deque(maxlen=capacity)

    def record(self, opportunity: dict) -> None:
        self._items.append(opportunity)

    def record_many(self, opportunities: list[dict]) -> None:
        self._items.extend(opportunities)

    def recent(self, limit: int = 50) -> list[dict]:
        items = list(self._items)
        return items[-limit:][::-1]

    def stats(self) -> dict:
        if not self._items:
            return {"count": 0, "avg_net_spread": 0.0, "max_net_spread": 0.0}
        spreads = [o["net_spread"] for o in self._items]
        return {
            "count": len(self._items),
            "avg_net_spread": sum(spreads) / len(spreads),
            "max_net_spread": max(spreads),
        }

    def clear(self) -> None:
        self._items.clear()
