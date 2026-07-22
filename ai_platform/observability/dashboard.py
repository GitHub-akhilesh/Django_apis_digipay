import logging
from typing import Dict, Any
from observability.cost import cost_analytics_engine
from observability.analytics import analytics_engine
from observability.health import health_aggregator
from observability.collector import metrics_collector

logger = logging.getLogger("ai_platform.observability.dashboard")

class DashboardEngine:
    @staticmethod
    def assemble_dashboard_summary() -> Dict[str, Any]:
        """Assembles executive operational metrics summary payload."""
        return {
            "health": health_aggregator.get_health_status(),
            "costs": cost_analytics_engine.get_cost_summary(),
            "analytics": analytics_engine.get_analytics_summary(),
            "traffic": {
                "totalLLMCalls": len(metrics_collector.llm_calls),
                "totalPlannerCalls": len(metrics_collector.planner_calls),
                "totalStreams": metrics_collector.streaming_stats["total_streams"]
            }
        }

dashboard_engine = DashboardEngine()
