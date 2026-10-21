"""FastAPI application: arbitrage monitor REST API + static dashboard."""
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import demo as demo_service
from . import live as live_service
from .alerts import AlertEngine
from .config import settings
from .core.arbitrage_graph import find_all_arbitrages
from .core.book import Level, OrderBook
from .core.detector import DetectorConfig, scan_pairs
from .core.fees import FeeSchedule
from .observability import (
    ObservabilityMiddleware,
    RateLimiter,
    RateLimitMiddleware,
    metrics,
    uptime_seconds,
)
from .persistence.history import OpportunityHistory
from .schemas import ArbitrageGraphRequest, DetectRequest

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Crypto Arbitrage Monitor",
    version=settings.version,
    description=(
        "MONITORING / ANALYTICS ONLY. Reports theoretical fee- and "
        "slippage-adjusted cross-venue spreads. Not trading advice."
    ),
)

app.add_middleware(GZipMiddleware, minimum_size=512)
if settings.rate_limit_per_sec > 0:
    app.add_middleware(RateLimitMiddleware, limiter=RateLimiter(settings.rate_limit_per_sec))
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": str(exc)})


if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

alert_engine = AlertEngine(settings.alert_cooldown_sec)
opportunity_history = OpportunityHistory(settings.history_capacity)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    index = _STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="dashboard not found")
    return FileResponse(str(index))


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "disclaimer": "monitoring only; not trading advice"}


@app.get("/api/version")
def version() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
    }


@app.get("/api/ready")
def ready() -> dict:
    return {"ready": True, "uptime_seconds": round(uptime_seconds(), 1)}


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> PlainTextResponse:
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


@app.post("/api/detect")
def detect(req: DetectRequest) -> dict:
    try:
        books = {
            b.venue: OrderBook(
                venue=b.venue,
                symbol=b.symbol,
                bids=[Level(p, s) for p, s in b.bids],
                asks=[Level(p, s) for p, s in b.asks],
                ts_exchange=b.ts_exchange,
                ts_recv=b.ts_recv,
            )
            for b in req.books
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    fees = {v: FeeSchedule(taker=f.taker, withdrawal=f.withdrawal) for v, f in req.fees.items()}
    now = req.now if req.now is not None else max(b.ts_recv for b in books.values())
    config = DetectorConfig(
        threshold=req.threshold,
        min_qty=req.min_qty,
        top_levels=req.top_levels,
        max_age=req.max_age,
    )
    opps = scan_pairs(books, fees, now, config)
    return {"now": now, "opportunities": [asdict(o) for o in opps]}


@app.get("/api/demo/books")
def demo_books() -> dict:
    return demo_service.demo_books()


@app.get("/api/demo/opportunities")
def demo_opportunities() -> dict:
    return demo_service.demo_opportunities()


@app.get("/api/demo/triangular")
def demo_triangular(profitable: bool = True) -> dict:
    return demo_service.demo_triangular(profitable=profitable)


@app.get("/api/demo/arbitrage-graph")
def demo_arbitrage_graph(profitable: bool = True) -> dict:
    """Multi-hop (Bellman-Ford) arbitrage over a synthetic conversion graph."""
    return demo_service.demo_arbitrage_graph(profitable=profitable)


@app.post("/api/arbitrage/graph")
def arbitrage_graph(req: ArbitrageGraphRequest) -> dict:
    """Find profitable conversion cycles of any length via Bellman-Ford."""
    rates = {(e.from_currency, e.to): e.rate for e in req.rates}
    try:
        cycles = find_all_arbitrages(rates, fee=req.fee, min_return=req.min_return)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "n_cycles": len(cycles),
        "cycles": [
            {"path": c.path, "rates": c.rates, "net_return": c.net_return} for c in cycles
        ],
    }


@app.get("/api/demo/history")
def demo_history() -> dict:
    return demo_service.demo_history()


@app.get("/api/demo/latency")
def demo_latency() -> dict:
    return demo_service.demo_latency()


@app.get("/api/demo/reliability")
def demo_reliability(n_frames: int = 20) -> dict:
    """Per-venue market-data reliability scores (crossed/stale/latency)."""
    return demo_service.demo_reliability(n_frames=max(2, min(n_frames, 500)))


@app.get("/api/demo/replay")
def demo_replay(n_frames: int = 40) -> dict:
    """Replay analytics: opportunity duration, max edge, and false-positive rate."""
    return demo_service.demo_replay(n_frames=max(2, min(n_frames, 1000)))


@app.get("/api/live/opportunities")
def live_opportunities(symbol: str = "BTC/USDT", allow_network: bool = True) -> dict:
    return live_service.live_opportunities(symbol, allow_network=allow_network)


@app.get("/api/alerts")
def alerts() -> dict:
    snapshot = demo_service.demo_opportunities()
    now = snapshot["now"]
    opps = snapshot["opportunities"]
    opportunity_history.record_many(opps)
    new_alerts = alert_engine.evaluate(opps, now)
    return {"now": now, "count": len(new_alerts), "alerts": [asdict(a) for a in new_alerts]}


@app.get("/api/history/recent")
def history_recent(limit: int = 50) -> dict:
    return {"recent": opportunity_history.recent(limit)}


@app.get("/api/history/stats")
def history_stats() -> dict:
    return opportunity_history.stats()
