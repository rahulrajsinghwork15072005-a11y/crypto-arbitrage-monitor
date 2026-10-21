"""Environment-driven application settings (no extra dependencies)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _csv(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "crypto-arbitrage-monitor"
    version: str = "1.2.0"
    environment: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    cors_origins: list[str] = field(
        default_factory=lambda: _csv(
            "CORS_ORIGINS",
            ["http://localhost:5182", "http://localhost:5173", "http://localhost:8082"],
        )
    )
    rate_limit_per_sec: int = int(os.getenv("RATE_LIMIT_PER_SEC", "0"))
    # Alert engine: per-(symbol,pair) cooldown between repeat alerts.
    alert_cooldown_sec: float = float(os.getenv("ALERT_COOLDOWN_SEC", "30"))
    # Max opportunity-history records kept in memory.
    history_capacity: int = int(os.getenv("HISTORY_CAPACITY", "1000"))


settings = Settings()
