import logging
from typing import Dict, Any

logger = logging.getLogger("ai_platform.evaluation.regression")

BASELINE_THRESHOLDS = {
    "overallScorePct": 85.0,
    "intentAccuracyPct": 90.0,
    "toolAccuracyPct": 80.0
}

class RegressionGuard:
    @staticmethod
    def verify_regression(current_scores: Dict[str, float]) -> bool:
        """Compare current evaluation performance against baseline specifications."""
        for metric, baseline in BASELINE_THRESHOLDS.items():
            current = current_scores.get(metric, 0.0)
            if current < baseline:
                logger.error(f"Regression detected for '{metric}': Current {current}% < Baseline {baseline}%")
                return False
        
        logger.info("Regression check passed. All performance metrics met or exceeded baselines.")
        return True

regression_guard = RegressionGuard()
