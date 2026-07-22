import logging
from typing import Dict, Any, List

logger = logging.getLogger("ai_platform.evaluation.scoring")

class EvaluationScorer:
    @staticmethod
    def calculate_scores(run_results: List[Dict[str, Any]], expected_dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics percentages from model run results vs expected specifications."""
        total = len(expected_dataset)
        intent_matches = 0
        tool_matches = 0
        param_matches = 0
        pattern_matches = 0

        for run, expected in zip(run_results, expected_dataset):
            # 1. Intent Match
            if run["intent"].lower() == expected["expected_intent"].lower():
                intent_matches += 1

            # 2. Tool Match
            actual_tools = set(run.get("selected_tools", []))
            expected_tools = set(expected["expected_tools"])
            if actual_tools == expected_tools:
                tool_matches += 1

            # 3. Parameters match
            actual_params = run.get("parameters", {})
            param_ok = True
            for p in expected["expected_params"]:
                if p not in actual_params:
                    param_ok = False
                    break
            if param_ok:
                param_matches += 1

            # 4. Response keyword matches
            res_body = run.get("response", "").lower()
            if expected["answer_pattern"].lower() in res_body:
                pattern_matches += 1

        intent_acc = (intent_matches / float(total)) * 100
        tool_acc = (tool_matches / float(total)) * 100
        param_acc = (param_matches / float(total)) * 100
        pattern_acc = (pattern_matches / float(total)) * 100
        
        overall_score = round((intent_acc + tool_acc + param_acc + pattern_acc) / 4.0, 2)

        return {
            "overallScorePct": overall_score,
            "intentAccuracyPct": round(intent_acc, 2),
            "toolAccuracyPct": round(tool_acc, 2),
            "parameterAccuracyPct": round(param_acc, 2),
            "responsePatternMatchPct": round(pattern_acc, 2)
        }

evaluation_scorer = EvaluationScorer()
