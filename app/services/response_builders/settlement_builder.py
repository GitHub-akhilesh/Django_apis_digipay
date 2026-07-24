from typing import Dict, Any

class SettlementResponseBuilder:
    @staticmethod
    def format_settlement(res: Dict[str, Any]) -> str:
        status = res.get("status")
        utr = res.get("utr") or "N/A"
        date_str = res.get("settlementDate") or "N/A"
        if status == "processed":
            return f"Settlement for your transaction is processed successfully on {date_str}. UTR: {utr}."
        elif status == "auto-reversal-initiated":
            return f"Settlement failed. Auto-reversal is initiated with UTR {utr}. Reversal ETA: 20 minutes."
        return f"Settlement status is {status}. Details: {res.get('failureReason', 'In progress')}."
