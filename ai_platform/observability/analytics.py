import logging
from typing import Dict, Any
from observability.collector import metrics_collector

logger = logging.getLogger("ai_platform.observability.analytics")

class AnalyticsEngine:
    @staticmethod
    def get_analytics_summary() -> Dict[str, Any]:
        """Compute pipeline analytics, intent distribution, and cache performance."""
        hits = metrics_collector.cache_stats["hits"]
        misses = metrics_collector.cache_stats["misses"]
        total_cache = hits + misses
        cache_hit_ratio = round((hits / float(total_cache or 1)) * 100, 2)

        total_intents = sum(metrics_collector.intent_counter.values()) or 1
        intent_distribution = {
            k: round((v / float(total_intents)) * 100, 2)
            for k, v in metrics_collector.intent_counter.items()
        }

        # Average latencies
        llm_latencies = [x["latencyMs"] for x in metrics_collector.llm_calls]
        avg_llm_latency = round(sum(llm_latencies) / float(len(llm_latencies) or 1), 2)

        planner_latencies = [x["latencyMs"] for x in metrics_collector.planner_calls]
        avg_planner_latency = round(sum(planner_latencies) / float(len(planner_latencies) or 1), 2)

        return {
            "cacheHitRatioPct": cache_hit_ratio,
            "cacheHits": hits,
            "cacheMisses": misses,
            "intentDistributionPct": intent_distribution,
            "averageLatenciesMs": {
                "llm": avg_llm_latency,
                "planner": avg_planner_latency
            }
        }

analytics_engine = AnalyticsEngine()
