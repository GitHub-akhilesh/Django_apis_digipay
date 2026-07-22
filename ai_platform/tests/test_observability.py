import pytest
import jwt
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from main import app
from core.config import settings
from observability.collector import metrics_collector
from observability.cost import cost_analytics_engine
from observability.analytics import analytics_engine
from observability.health import health_aggregator

client = TestClient(app)

def generate_test_token(csc_id: str = "500100100014") -> str:
    payload = {
        "sub": "testuser",
        "cscId": csc_id,
        "roles": ["ROLE_USER", "ROLE_MERCHANT"],
        "exp": int(datetime.now(UTC).timestamp()) + 3600
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def test_collector_recording():
    metrics_collector.record_llm_call(
        provider="openai",
        model="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
        cost=0.0015,
        latency_ms=120.0
    )
    metrics_collector.record_planner_call("WALLET", 45.0, 1)
    metrics_collector.record_cache(hit=True)

    summary = cost_analytics_engine.get_cost_summary()
    assert summary["totalTokens"] >= 150
    assert summary["totalCostUSD"] > 0.0

    analytics = analytics_engine.get_analytics_summary()
    assert analytics["cacheHits"] >= 1
    assert "WALLET" in analytics["intentDistributionPct"]

def test_health_aggregator():
    status = health_aggregator.get_health_status()
    assert status["overallStatus"] == "HEALTHY"
    assert status["components"]["corePlatform"] == "UP"

def test_observability_endpoints():
    token = generate_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Test Summary Endpoint
    res_summary = client.get("/api/v1/observability/summary", headers=headers)
    assert res_summary.status_code == 200
    assert res_summary.json()["success"] is True
    assert "health" in res_summary.json()["data"]
    assert "costs" in res_summary.json()["data"]

    # 2. Test Costs Endpoint
    res_costs = client.get("/api/v1/observability/costs", headers=headers)
    assert res_costs.status_code == 200
    assert res_costs.json()["success"] is True
    assert "providerCostBreakdown" in res_costs.json()["data"]
