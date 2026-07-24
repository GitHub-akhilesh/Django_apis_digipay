from typing import Dict, Any
from datetime import datetime, timedelta

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

    @staticmethod
    def format_last_settlement(res: Dict[str, Any]) -> str:
        date_str = res.get("lastSettlementDate") or res.get("settlementDate") or "N/A"
        amt = float(res.get("lastSettlementAmount") or res.get("amount") or 0.0)
        from_date = res.get("fromDate")
        to_date = res.get("toDate")
        if not from_date or not to_date:
            now = datetime.now()
            from_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            to_date = now.strftime("%Y-%m-%d")
        return f"Your last settlement was processed on {date_str} for ₹{amt:.2f}. (Period: {from_date} to {to_date})"
