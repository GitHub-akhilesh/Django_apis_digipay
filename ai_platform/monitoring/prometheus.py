import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ai_platform.monitoring.prometheus")

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    REQUEST_COUNTER = Counter(
        "ai_platform_requests_total",
        "Total requests processed by the AI Platform",
        ["endpoint", "intent"]
    )
    LATENCY_HISTOGRAM = Histogram(
        "ai_platform_request_latency_seconds",
        "AI Platform request processing latency in seconds",
        ["endpoint"]
    )
    TOKEN_COUNTER = Counter(
        "ai_platform_token_usage_total",
        "Total estimated tokens consumed",
        ["model", "type"]
    )
    ERROR_COUNTER = Counter(
        "ai_platform_errors_total",
        "Total exceptions or errors encountered",
        ["type"]
    )
    ESCALATION_COUNTER = Counter(
        "ai_platform_escalations_total",
        "Total conversations escalated to Level-2/3 support"
    )
else:
    class MockMetric:
        def __init__(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def inc(self, amount=1): pass
        def observe(self, amount): pass
        def set(self, amount): pass

    REQUEST_COUNTER = MockMetric()
    LATENCY_HISTOGRAM = MockMetric()
    TOKEN_COUNTER = MockMetric()
    ERROR_COUNTER = MockMetric()
    ESCALATION_COUNTER = MockMetric()


class PlatformMetrics:
    @staticmethod
    def record_request(endpoint: str, intent: str):
        logger.info(f"METRIC: Request on {endpoint} | Intent: {intent}")
        try:
            REQUEST_COUNTER.labels(endpoint=endpoint, intent=intent).inc()
        except Exception:
            pass

    @staticmethod
    def record_latency(endpoint: str, duration_sec: float):
        logger.info(f"METRIC: Latency on {endpoint} | Duration: {duration_sec:.4f}s")
        try:
            LATENCY_HISTOGRAM.labels(endpoint=endpoint).observe(duration_sec)
        except Exception:
            pass

    @staticmethod
    def record_tokens(model: str, input_tokens: int, output_tokens: int):
        logger.info(f"METRIC: Tokens on {model} | Input: {input_tokens} | Output: {output_tokens}")
        try:
            TOKEN_COUNTER.labels(model=model, type="input").inc(input_tokens)
            TOKEN_COUNTER.labels(model=model, type="output").inc(output_tokens)
        except Exception:
            pass

    @staticmethod
    def record_error(error_type: str):
        logger.error(f"METRIC: Error | Type: {error_type}")
        try:
            ERROR_COUNTER.labels(type=error_type).inc()
        except Exception:
            pass

    @staticmethod
    def record_escalation():
        logger.info("METRIC: Escalation triggered!")
        try:
            ESCALATION_COUNTER.inc()
        except Exception:
            pass


class TraceTracker:
    @staticmethod
    def extract_or_generate_trace(headers: Dict[str, str]) -> Dict[str, str]:
        """
        Parses B3/Zipkin tracing headers from incoming requests,
        generating new trace variables if not present.
        """
        trace_id = headers.get("x-b3-traceid") or headers.get("X-B3-TraceId")
        span_id = headers.get("x-b3-spanid") or headers.get("X-B3-SpanId")
        
        if not trace_id:
            import uuid
            trace_id = uuid.uuid4().hex
            span_id = uuid.uuid4().hex[:16]
            logger.debug(f"Generated new Zipkin traceId: {trace_id}")
        else:
            logger.debug(f"Propagating Zipkin traceId: {trace_id} | spanId: {span_id}")
            
        return {
            "X-B3-TraceId": trace_id,
            "X-B3-SpanId": span_id,
            "X-B3-Sampled": "1"
        }
