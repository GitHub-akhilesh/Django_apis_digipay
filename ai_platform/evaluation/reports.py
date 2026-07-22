from typing import Dict, Any

class EvaluationReporter:
    @staticmethod
    def print_text_report(scores: Dict[str, Any], hallucination_rate: float, avg_latency: float, avg_cost: float) -> str:
        """Formats clear executive summary cards for CLI."""
        report = []
        report.append("==================================================")
        report.append("          D DAP AI EVALUATION REPORT              ")
        report.append("==================================================")
        report.append(f"OVERALL QUALITY SCORE : {scores['overallScorePct']}%")
        report.append(f"Intent Accuracy       : {scores['intentAccuracyPct']}%")
        report.append(f"Tool Selection Acc    : {scores['toolAccuracyPct']}%")
        report.append(f"Parameter Match Acc   : {scores['parameterAccuracyPct']}%")
        report.append(f"Response Keyword Match: {scores['responsePatternMatchPct']}%")
        report.append("--------------------------------------------------")
        report.append(f"Hallucination Rate    : {hallucination_rate}%")
        report.append(f"Average Latency       : {avg_latency:.2f} ms")
        report.append(f"Average Cost          : ${avg_cost:.6f}")
        report.append("==================================================")
        return "\n".join(report)

evaluation_reporter = EvaluationReporter()
