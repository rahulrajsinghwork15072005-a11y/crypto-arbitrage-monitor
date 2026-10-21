from fastapi.testclient import TestClient

from app.alerts import AlertEngine
from app.main import app
from app.persistence.history import OpportunityHistory

client = TestClient(app)


def _opp(net=0.001, profit=10.0):
    return {
        "symbol": "BTC-USD",
        "buy_venue": "COINBASE",
        "sell_venue": "KRAKEN",
        "net_spread": net,
        "est_profit": profit,
    }


def test_alert_cooldown_throttling():
    engine = AlertEngine(cooldown=30.0)
    opps = [_opp()]
    assert len(engine.evaluate(opps, now=1000.0)) == 1   # first fires
    assert len(engine.evaluate(opps, now=1005.0)) == 0   # within cooldown -> suppressed
    assert len(engine.evaluate(opps, now=1040.0)) == 1   # cooldown elapsed -> fires again


def test_history_capacity_and_stats():
    history = OpportunityHistory(capacity=3)
    for i in range(5):
        history.record({"net_spread": i / 1000.0})
    recent = history.recent(10)
    assert len(recent) == 3                  # bounded by capacity
    assert recent[0]["net_spread"] == 0.004  # most recent first
    assert history.stats()["count"] == 3


def test_alerts_endpoint():
    body = client.get("/api/alerts").json()
    assert "alerts" in body
    assert "count" in body


def test_history_endpoints():
    client.get("/api/alerts")
    assert "recent" in client.get("/api/history/recent").json()
    assert "count" in client.get("/api/history/stats").json()
