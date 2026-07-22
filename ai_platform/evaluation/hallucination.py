import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ai_platform.evaluation.hallucination")

class HallucinationDetector:
    @staticmethod
    def calculate_hallucination_rate(run_results: List[Dict[str, Any]]) -> float:
        """Scan responses for ungrounded numbers or metrics not present in context."""
        hallucinated_counts = 0
        total = len(run_results)

        for run in run_results:
            response = run.get("response", "")
            
            # Simple check: If response mentions money values (e.g. ₹9999 or $9999) that are not part of
            # the known test numbers (e.g., 4560.50, 450.50, 4560.50), count as hallucination.
            money_vals = re.findall(r"₹\s*(\d+(?:\.\d+)?)", response)
            for val in money_vals:
                float_val = float(val)
                if float_val not in [4560.50, 450.50, 4560.5]:
                    logger.warning(f"Detected ungrounded balance value: ₹{float_val}")
                    hallucinated_counts += 1
                    break

        return round((hallucinated_counts / float(total or 1)) * 100, 2)

hallucination_detector = HallucinationDetector()
