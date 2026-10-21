# Crypto Arbitrage Monitor

A real-time **monitoring** system that streams normalized order books, computes
**fee- and slippage-adjusted** cross-venue spreads against real book depth,
filters by liquidity and freshness, scans **triangular** cycles, and tracks
opportunity **decay**.

> **Monitoring / analytics only.** Theoretical spreads net of fees and book
> slippage. Not trading advice; no orders are placed. Latency, withdrawal limits,
> and market movement routinely erase raw spreads.

See [PLAN.md](PLAN.md) for the full design and math, and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system architecture (the book,
fees/slippage, the detector, and the Bellman-Ford multi-hop arbitrage search).

## What's implemented

| Layer | Status |
|-------|--------|
| Core (`app/core`) | order book, VWAP fills + slippage, fee model, depth-aware max executable size, liquidity/freshness filters, triangular scanner, **Bellman-Ford multi-hop arbitrage**, latency stats, opportunity detector |
| Data (`app/data`) | synthetic multi-venue books, decaying-edge history, latency samples |
| API (`app/main.py`) | FastAPI REST + OpenAPI docs |
| Dashboard (`app/static`) | Plotly dashboard (depth ladders, opportunities, decay, latency) |
| Tests (`tests/`) | 52 unit + API tests (incl. Bellman-Ford negative-cycle detection) |

State is in-memory (no database). A production deployment would add exchange
WebSocket collectors and a Redis/streams layer (see [PLAN.md](PLAN.md)); these are
**roadmap** items — the detector core stays unchanged.

## Run it

```powershell
# from crypto-arbitrage-monitor/backend/
& ..\.venv\Scripts\python.exe -m pip install -r requirements.txt
& ..\.venv\Scripts\python.exe -m pytest -q
& ..\.venv\Scripts\python.exe scripts\bench.py        # Bellman-Ford + detector throughput
& ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

- Dashboard: http://127.0.0.1:8002/
- Swagger docs: http://127.0.0.1:8002/docs

## Key endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/detect` | detect opportunities from supplied books |
| GET | `/api/demo/books` | current synthetic venue books |
| GET | `/api/demo/opportunities` | detected fee-adjusted opportunities |
| GET | `/api/demo/triangular` | triangular cycle (toggle `profitable`) |
| GET | `/api/demo/arbitrage-graph` | multi-hop (Bellman-Ford) arbitrage cycles |
| POST | `/api/arbitrage/graph` | find arbitrage cycles in supplied conversion rates |
| GET | `/api/demo/history` | net-spread decay + edge lifetime |
| GET | `/api/demo/latency` | per-venue latency stats |
| GET | `/api/demo/reliability` | per-venue market-data reliability scores |
| GET | `/api/demo/replay` | replay analytics (duration, false-positive rate) |

## Live data (optional)

Real exchange order books via ccxt, with an offline fallback (returns a note when
the network/ccxt is unavailable):

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/live/opportunities?symbol=BTC/USDT` | detect on live multi-venue books |

## React frontend (Vite)

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5182 (dev proxy /api -> :8002)
npm run build      # production build to dist/
```

## Docker

```powershell
docker compose up --build
# frontend: http://localhost:8082  |  API: http://localhost:8002
```

## Production & operations

- Observability: `GET /api/version`, `GET /api/ready`, `GET /metrics` (Prometheus text format).
- Middleware: CORS, GZip, request-id + security headers, structured request logs, optional rate limiting.
- Env config: `CORS_ORIGINS`, `LOG_LEVEL`, `RATE_LIMIT_PER_SEC`, `ALERT_COOLDOWN_SEC`, `HISTORY_CAPACITY`.

## Alerting & history

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/alerts` | throttled (cooldown) arbitrage alerts |
| GET | `/api/history/recent` | recent detected opportunities |
| GET | `/api/history/stats` | opportunity-history aggregates |

## Known limitations & roadmap

**Limitations**
- Monitoring/analytics only — **no orders are placed**.
- State is in-memory (no database); live books come from a single optional ccxt
  fetch with a synthetic fallback.

**Roadmap**
- WebSocket collectors + Redis streams; SQLite/PostgreSQL persistence of
  opportunities, latency and alerts.
- Historical replay analytics (opportunity duration, max edge, false-positive
  rate) and venue reliability scoring (crossed-book / stale / latency) are
  implemented: `GET /api/demo/replay`, `GET /api/demo/reliability`.
