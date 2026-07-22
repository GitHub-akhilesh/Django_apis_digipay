import logging
from typing import Dict, Any
from performance.load_runner import load_runner
from performance.reports import performance_reporter

logger = logging.getLogger("ai_platform.performance.benchmark")

class PerformanceBenchmark:
    @staticmethod
    async def run_benchmark(concurrent_users: int, total_requests: int) -> Dict[str, Any]:
        """Trigger load generation and return formatted stats."""
        logger.info(f"Triggering Performance Profile: Concurrent={concurrent_users}, Requests={total_requests}")
        stats = await load_runner.execute_load(concurrent_users, total_requests)
        report_text = performance_reporter.print_performance_report(stats)
        print(report_text)
        return {
            "stats": stats,
            "report": report_text
        }

performance_benchmark = PerformanceBenchmark()
