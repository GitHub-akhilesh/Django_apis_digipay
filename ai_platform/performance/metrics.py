import math
from typing import List, Dict, Any

class PerformanceMetricsCollector:
    def __init__(self):
        self.latencies: List[float] = []
        self.cache_hits: int = 0
        self.total_requests: int = 0

    def record_request(self, latency_ms: float, cache_hit: bool):
        """Record details of a simulated client API request."""
        self.latencies.append(latency_ms)
        self.total_requests += 1
        if cache_hit:
            self.cache_hits += 1

    def get_percentile(self, percentile: float) -> float:
        """Calculate percentile value from recorded latencies."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = (len(sorted_latencies) - 1) * (percentile / 100.0)
        floor = math.floor(idx)
        ceil = math.ceil(idx)
        if floor == ceil:
            return sorted_latencies[int(idx)]
        return sorted_latencies[floor] * (ceil - idx) + sorted_latencies[ceil] * (idx - floor)

    def calculate_stats(self, duration_sec: float) -> Dict[str, Any]:
        """Compute summary statistics for the execution run."""
        tps = self.total_requests / duration_sec if duration_sec > 0 else 0
        cache_ratio = (self.cache_hits / self.total_requests * 100) if self.total_requests > 0 else 0.0
        
        return {
            "totalRequests": self.total_requests,
            "tps": round(tps, 2),
            "p50": round(self.get_percentile(50.0), 2),
            "p90": round(self.get_percentile(90.0), 2),
            "p95": round(self.get_percentile(95.0), 2),
            "p99": round(self.get_percentile(99.0), 2),
            "cacheHitRatioPct": round(cache_ratio, 2)
        }

metrics_collector = PerformanceMetricsCollector()
