import time
import logging
from typing import Dict, Any, List
from collections import defaultdict, Counter

logger = logging.getLogger("ai_platform.observability.collector")

class MetricsCollector:
    def __init__(self):
        self.llm_calls: List[Dict[str, Any]] = []
        self.planner_calls: List[Dict[str, Any]] = []
        self.gateway_calls: List[Dict[str, Any]] = []
        self.cache_stats = {"hits": 0, "misses": 0}
        self.intent_counter = Counter()
        self.provider_counter = Counter()
        self.streaming_stats = {"total_streams": 0, "total_tokens": 0}

    def record_llm_call(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int, cost: float, latency_ms: float, retries: int = 0, fallback: bool = False):
        entry = {
            "timestamp": time.time(),
            "provider": provider,
            "model": model,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "cost": cost,
            "latencyMs": latency_ms,
            "retries": retries,
            "fallback": fallback
        }
        self.llm_calls.append(entry)
        self.provider_counter[provider] += 1
        logger.debug(f"Recorded LLM call: {provider} (${cost:.6f})")

    def record_planner_call(self, intent: str, latency_ms: float, tools_count: int):
        entry = {
            "timestamp": time.time(),
            "intent": intent,
            "latencyMs": latency_ms,
            "toolsCount": tools_count
        }
        self.planner_calls.append(entry)
        self.intent_counter[intent] += 1

    def record_gateway_call(self, service: str, endpoint: str, latency_ms: float, status_code: int):
        entry = {
            "timestamp": time.time(),
            "service": service,
            "endpoint": endpoint,
            "latencyMs": latency_ms,
            "statusCode": status_code
        }
        self.gateway_calls.append(entry)

    def record_cache(self, hit: bool):
        if hit:
            self.cache_stats["hits"] += 1
        else:
            self.cache_stats["misses"] += 1

    def record_streaming(self, tokens_count: int, duration_ms: float):
        self.streaming_stats["total_streams"] += 1
        self.streaming_stats["total_tokens"] += tokens_count

metrics_collector = MetricsCollector()
