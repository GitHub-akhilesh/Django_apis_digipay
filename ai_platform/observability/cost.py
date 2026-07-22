import time
import logging
from typing import Dict, Any
from observability.collector import metrics_collector

logger = logging.getLogger("ai_platform.observability.cost")

class CostAnalyticsEngine:
    @staticmethod
    def get_cost_summary() -> Dict[str, Any]:
        """Compute cost distribution, daily/monthly estimates, and provider breakdown."""
        llm_calls = metrics_collector.llm_calls
        total_cost = sum(x["cost"] for x in llm_calls)
        total_tokens = sum(x["promptTokens"] + x["completionTokens"] for x in llm_calls)
        
        provider_costs = {}
        for x in llm_calls:
            prov = x["provider"]
            provider_costs[prov] = round(provider_costs.get(prov, 0.0) + x["cost"], 6)

        avg_cost_per_query = round(total_cost / float(len(llm_calls) or 1), 6)
        
        # Monthly projection (30 days based on active calls)
        projected_monthly = round(total_cost * 30, 2)

        return {
            "totalCostUSD": round(total_cost, 4),
            "projectedMonthlyUSD": projected_monthly,
            "totalTokens": total_tokens,
            "averageCostPerQueryUSD": avg_cost_per_query,
            "providerCostBreakdown": provider_costs
        }

cost_analytics_engine = CostAnalyticsEngine()
