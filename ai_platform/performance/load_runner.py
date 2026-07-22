import time
import asyncio
from typing import Dict, Any
from performance.metrics import PerformanceMetricsCollector
from agent.orchestrator import AgentOrchestrator

class ConcurrencyLoadRunner:
    @staticmethod
    async def execute_load(concurrent_users: int, total_requests: int) -> Dict[str, Any]:
        """Simulate concurrent client load using the orchestrator runtime."""
        collector = PerformanceMetricsCollector()
        sem = asyncio.Semaphore(concurrent_users)
        start_time = time.time()

        async def worker(idx: int):
            async with sem:
                w_start = time.time()
                try:
                    res = await AgentOrchestrator.chat(
                        session_id=f"load_session_{idx}",
                        message="What is my wallet balance?",
                        csc_id="500100100014",
                        history=[]
                    )
                    latency = (time.time() - w_start) * 1000
                    explainability = res.get("explainability", {})
                    # simulate cache hit if execution time is zero
                    cache_hit = explainability.get("executionTimeMs", 1.0) == 0.0
                    collector.record_request(latency, cache_hit)
                except Exception:
                    collector.record_request((time.time() - w_start) * 1000, False)

        tasks = [worker(i) for i in range(total_requests)]
        await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        return collector.calculate_stats(duration)

load_runner = ConcurrencyLoadRunner()
