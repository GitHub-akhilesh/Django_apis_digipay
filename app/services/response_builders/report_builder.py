from typing import Dict, Any

class ReportResponseBuilder:
    @staticmethod
    def format_daywise_report(res: Dict[str, Any]) -> str:
        return f"Daywise report for {res.get('yearMonth', 'requested month')}: Available for download at {res.get('downloadUrl')}."
