import time
import logging

try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger("ai_platform.monitoring.metrics")

if PROMETHEUS_AVAILABLE:
    # 1. Counter (Total HTTP request counts)
    HTTP_REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests received",
        ["method", "endpoint", "status"]
    )
    # 2. Histogram (Response latency)
    HTTP_REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["endpoint"]
    )
    # 3. Gauge (Active WebSocket connections count)
    ACTIVE_WS_CONNECTIONS = Gauge(
        "active_websocket_connections",
        "Total active real-time websocket connections"
    )
    # 4. Summary (RAG retrieval times)
    RAG_RETRIEVAL_LATENCY = Summary(
        "rag_retrieval_duration_seconds",
        "RAG context search processing latency in seconds"
    )
else:
    class MockMetric:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def inc(self, amount=1): pass
        def dec(self, amount=1): pass
        def observe(self, amount): pass
        def set(self, amount): pass

    HTTP_REQUEST_COUNT = MockMetric()
    HTTP_REQUEST_LATENCY = MockMetric()
    ACTIVE_WS_CONNECTIONS = MockMetric()
    RAG_RETRIEVAL_LATENCY = MockMetric()


def record_http_request(method: str, endpoint: str, status: int):
    try:
        HTTP_REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    except Exception as e:
        logger.debug(f"Metrics record failed: {e}")

def record_http_latency(endpoint: str, duration: float):
    try:
        HTTP_REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
    except Exception as e:
        logger.debug(f"Metrics observe failed: {e}")

def record_ws_connect():
    try:
        ACTIVE_WS_CONNECTIONS.inc()
    except Exception:
        pass

def record_ws_disconnect():
    try:
        ACTIVE_WS_CONNECTIONS.dec()
    except Exception:
        pass

def record_rag_latency(duration: float):
    try:
        RAG_RETRIEVAL_LATENCY.observe(duration)
    except Exception:
        pass
