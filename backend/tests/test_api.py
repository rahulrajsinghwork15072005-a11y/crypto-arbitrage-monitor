from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_has_disclaimer():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "trading advice" in r.json()["disclaimer"]


def test_dashboard():
    r = client.get("/")
    assert r.status_code == 200
    assert "Arbitrage" in r.text


def test_demo_opportunities():
    r = client.get("/api/demo/opportunities")
    assert r.status_code == 200
    opps = r.json()["opportunities"]
    assert len(opps) >= 1
    assert opps[0]["buy_venue"] == "COINBASE"


def test_demo_triangular_toggle():
    assert client.get("/api/demo/triangular?profitable=true").json()["is_opportunity"] is True
    assert client.get("/api/demo/triangular?profitable=false").json()["is_opportunity"] is False


def test_demo_history_and_latency():
    h = client.get("/api/demo/history").json()
    assert "decay_rate" in h and h["lifetime"] > 0
    lat = client.get("/api/demo/latency").json()
    assert "BINANCE" in lat


def test_detect_endpoint():
    payload = {
        "books": [
            {"venue": "A", "symbol": "BTC-USD", "bids": [[100, 5]], "asks": [[100.1, 5]], "ts_recv": 1000},
            {"venue": "B", "symbol": "BTC-USD", "bids": [[101, 5]], "asks": [[101.1, 5]], "ts_recv": 1000},
        ],
        "now": 1000, "threshold": 0.0005, "min_qty": 1, "top_levels": 1, "max_age": 5,
    }
    r = client.post("/api/detect", json=payload)
    assert r.status_code == 200
    opps = r.json()["opportunities"]
    assert len(opps) >= 1
    assert opps[0]["buy_venue"] == "A"
