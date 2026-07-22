import time
import asyncio
import tracemalloc
from typing import Dict, Any
from agent.orchestrator import AgentOrchestrator

class SoakRunner:
    @staticmethod
    async def execute_soak(iterations: int) -> Dict[str, Any]:
        """Runs iterative executions monitoring memory allocations to detect leaks."""
        tracemalloc.start()
        start_snapshot = tracemalloc.take_snapshot()
        
        start_time = time.time()
        for idx in range(iterations):
            try:
                await AgentOrchestrator.chat(
                    session_id=f"soak_session_{idx}",
                    message="Check limits",
                    csc_id="500100100014",
                    history=[]
                )
            except Exception:
                pass
            await asyncio.sleep(0.01)

        end_snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        
        stats = end_snapshot.compare_to(start_snapshot, "lineno")
        total_growth_kb = sum(stat.size_diff for stat in stats) / 1024.0
        duration = time.time() - start_time

        return {
            "iterations": iterations,
            "durationSec": round(duration, 2),
            "memoryGrowthKB": round(total_growth_kb, 2),
            "stable": total_growth_kb < 5000.0  # Stable if growth < 5MB for the test duration
        }

soak_runner = SoakRunner()
