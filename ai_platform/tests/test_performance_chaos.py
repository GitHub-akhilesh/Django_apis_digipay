import pytest
from performance.metrics import PerformanceMetricsCollector
from performance.load_runner import load_runner
from performance.soak_runner import soak_runner
from performance.benchmark import performance_benchmark
from chaos.redis_failure import redis_failure_simulator
from chaos.llm_failure import llm_failure_simulator
from chaos.gateway_failure import gateway_failure_simulator
from chaos.network_failure import network_latency_simulator
from services.cache_service import cache_service
from llm.orchestrator import llm_orchestrator
from gateway.client import GatewayClient
from agent.orchestrator import AgentOrchestrator

def test_performance_metrics_percentiles():
    collector = PerformanceMetricsCollector()
    for lat in range(1, 101):
        collector.record_request(float(lat), cache_hit=(lat % 10 == 0))
    stats = collector.calculate_stats(10.0)
    assert stats["totalRequests"] == 100
    assert stats["p50"] == 50.5
    assert stats["p95"] == 95.05
    assert stats["cacheHitRatioPct"] == 10.0

@pytest.mark.anyio
async def test_load_and_soak_runners(monkeypatch):
    async def mock_chat(session_id, message, csc_id, history, **kwargs):
        return {
            "response": "Fast response",
            "intent": "Wallet",
            "escalate": False,
            "policy_checked": True,
            "explainability": {"executionTimeMs": 5.0}
        }
    monkeypatch.setattr(AgentOrchestrator, "chat", mock_chat)

    load_stats = await load_runner.execute_load(concurrent_users=2, total_requests=4)
    assert load_stats["totalRequests"] == 4

    soak_stats = await soak_runner.execute_soak(iterations=2)
    assert soak_stats["iterations"] == 2
    assert soak_stats["stable"] is True

    bench = await performance_benchmark.run_benchmark(concurrent_users=2, total_requests=2)
    assert bench["stats"]["totalRequests"] == 2

def test_redis_failure_chaos():
    # Inject
    redis_failure_simulator.inject_failure()
    with pytest.raises(ConnectionError):
        cache_service.get_cached_result("getWalletBalance", {})

    # Recover
    redis_failure_simulator.recover()
    cache_service.get_cached_result("getWalletBalance", {}) # No exception

def test_llm_failure_chaos():
    original = list(llm_orchestrator.priority_list)
    # Inject
    llm_failure_simulator.inject_primary_failure()
    assert "openai" not in llm_orchestrator.priority_list

    # Recover
    llm_failure_simulator.recover()
    assert llm_orchestrator.priority_list == original

@pytest.mark.anyio
async def test_gateway_timeout_and_latency_chaos():
    # Inject Timeout
    gateway_failure_simulator.inject_timeout_failure()
    with pytest.raises(TimeoutError):
        await GatewayClient.request("GET", "/test")
    gateway_failure_simulator.recover()

    # Inject Latency
    network_latency_simulator.inject_latency(0.1)
    # Restore mock request inside test to verify timing
    async def fast_mock(*args, **kwargs):
        return {"ok": True}
    network_latency_simulator._original_request = fast_mock

    import time
    start = time.time()
    await GatewayClient.request("GET", "/test")
    elapsed = time.time() - start
    assert elapsed >= 0.1
    network_latency_simulator.recover()
