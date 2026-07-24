from typing import Dict, Any

class TransactionResponseBuilder:
    @staticmethod
    def format_transaction(res: Dict[str, Any]) -> str:
        status = res.get("status")
        amt = res.get("amount", 0.0)
        date_str = res.get("date") or "N/A"
        if status == "SUCCESS":
            return f"Transaction {res['txnId']} of ₹{amt:.2f} was successful on {date_str}. UTR: {res.get('utr', 'N/A')}."
        elif status == "FAILED":
            reason = res.get("failureReason", "Unknown error")
            settlement_status = res.get("settlementStatus")
            reversal_msg = " An automatic reversal has already been initiated and should credit back to the bank account shortly (typically within 20 minutes)." if settlement_status == "auto-reversal-initiated" else ""
            return f"Transaction {res['txnId']} of ₹{amt:.2f} failed on {date_str} due to: {reason}.{reversal_msg}"
        return f"Transaction {res['txnId']} status is {status}. Amount: ₹{amt:.2f}."

    @staticmethod
    def format_txn_logs(res: Dict[str, Any]) -> str:
        return f"Retrieved {res.get('totalRecords', 0)} transaction log(s) for your account between {res.get('fromDate')} and {res.get('toDate')}."

    @staticmethod
    def format_statement(res: Dict[str, Any]) -> str:
        return f"Passbook statement compiled with {res.get('totalTransactions', 0)} transaction(s) total volume ₹{res.get('totalVolume', 0.0):.2f}. Available at {res.get('downloadUrl')}."
