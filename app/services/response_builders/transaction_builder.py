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
        logs = res.get("data") or res.get("logs") or res.get("transactions") or []
        if not logs:
            return f"No transaction logs found for your account between {res.get('fromDate')} and {res.get('toDate')}."
        
        display_logs = logs[:10]
        lines = [f"Here are your last {len(display_logs)} transaction log(s) (Total records: {res.get('totalRecords', len(logs))}):"]
        for idx, item in enumerate(display_logs, 1):
            txn_id = item.get("txnId") or item.get("txn_id") or "N/A"
            amt = float(item.get("amount") or item.get("lgrAmt") or 0.0)
            st = item.get("status", "SUCCESS")
            type_str = item.get("type") or item.get("category") or "Txn"
            dt = item.get("created_at") or item.get("date") or "N/A"
            lines.append(f"{idx}. [{type_str}] Amount: ₹{amt:.2f} | Status: {st} | Txn ID: {txn_id} | Date: {dt}")
        return "\n".join(lines)

    @staticmethod
    def format_statement(res: Dict[str, Any]) -> str:
        return f"Passbook statement compiled with {res.get('totalTransactions', 0)} transaction(s) total volume ₹{res.get('totalVolume', 0.0):.2f}. Available at {res.get('downloadUrl')}."
