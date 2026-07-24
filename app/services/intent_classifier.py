import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.schemas.enums import ToolName

logger = logging.getLogger("digipay")

class IntentClassifier:
    """Intent Classification Engine combining rule-based heuristics and LLM capability."""

    @staticmethod
    def _extract_date_range(msg: str) -> tuple[str, str, bool]:
        now = datetime.now()
        msg_lower = msg.lower()

        # 1. ISO dates YYYY-MM-DD
        iso_dates = re.findall(r'\b(\d{4}-\d{2}-\d{2})\b', msg)
        if len(iso_dates) >= 2:
            return iso_dates[0], iso_dates[1], True
        elif len(iso_dates) == 1:
            return iso_dates[0], now.strftime("%Y-%m-%d"), True

        # 2. Indian dates DD-MM-YYYY or DD/MM/YYYY
        in_dates = re.findall(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', msg)
        if len(in_dates) >= 2:
            d1 = f"{in_dates[0][2]}-{int(in_dates[0][1]):02d}-{int(in_dates[0][0]):02d}"
            d2 = f"{in_dates[1][2]}-{int(in_dates[1][1]):02d}-{int(in_dates[1][0]):02d}"
            return d1, d2, True
        elif len(in_dates) == 1:
            d1 = f"{in_dates[0][2]}-{int(in_dates[0][1]):02d}-{int(in_dates[0][0]):02d}"
            return d1, now.strftime("%Y-%m-%d"), True

        # 3. Relative day counts: e.g. "last 7 days", "14 days", "last 60 days"
        days_match = re.search(r'(?:last\s+)?(\d+)\s*days?', msg_lower)
        if days_match:
            num_days = int(days_match.group(1))
            from_dt = now - timedelta(days=num_days)
            return from_dt.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"), True

        # 4. Keywords: today, yesterday
        if "today" in msg_lower:
            t_str = now.strftime("%Y-%m-%d")
            return t_str, t_str, True
        if "yesterday" in msg_lower:
            y_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            return y_str, y_str, True

        # 5. Default fallback: last 30 days
        from_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")
        return from_date, to_date, False

    @staticmethod
    def classify_intent(last_msg: str, csc_id: str) -> Dict[str, Any]:
        msg_lower = last_msg.lower()
        from_date, to_date, is_explicit = IntentClassifier._extract_date_range(last_msg)
        txn_id_match = re.search(r'(CZU[A-Z0-9]+|TKT-[A-Z0-9]+)', last_msg, re.IGNORECASE)
        entity_id = txn_id_match.group(1) if txn_id_match else None

        intent = "General"
        confidence = 0.95
        tool_calls = []

        if any(k in msg_lower for k in ["old digipay", "old balance", "legacy balance", "legacy system", "legacy system wallet", "old wallet"]):
            intent = "Wallet"
            tool_calls.append({"name": ToolName.GET_OLD_DIGIPAY_BALANCE.value, "args": {"merchantId": csc_id}})
        elif any(k in msg_lower for k in ["wallet balance", "what is my wallet balance", "check my wallet balance", "my wallet balance", "balance", "money in wallet", "wallet amount"]):
            intent = "Wallet"
            tool_calls.append({"name": ToolName.GET_WALLET_BALANCE.value, "args": {"merchantId": csc_id}})
        elif any(k in msg_lower for k in ["txn logs", "transaction logs", "logs", "last txn", "last transaction", "transactions", "old system txn", "old system transaction", "txn"]):
            intent = "Wallet"
            tool_calls.append({
                "name": ToolName.GET_TXN_LOGS.value,
                "args": {
                    "merchantId": csc_id,
                    "fromDate": from_date,
                    "toDate": to_date,
                    "rpp": 10,
                    "cp": 1
                }
            })
        elif any(k in msg_lower for k in ["statement", "report", "passbook", "history"]):
            intent = "Wallet"
            tool_calls.append({
                "name": ToolName.GENERATE_STATEMENT.value,
                "args": {
                    "merchantId": csc_id,
                    "fromDate": from_date,
                    "toDate": to_date
                }
            })
        elif any(k in msg_lower for k in ["daywise", "monthly report"]):
            intent = "Wallet"
            tool_calls.append({"name": ToolName.GET_DAYWISE_REPORT.value, "args": {"merchantId": csc_id, "yearMonth": "2026 June"}})
        elif any(k in msg_lower for k in ["kyc", "verify profile", "account active"]):
            intent = "KYC"
            tool_calls.append({"name": ToolName.GET_KYC_STATUS.value, "args": {"merchantId": csc_id}})
        elif any(k in msg_lower for k in ["bank account", "account details", "linked bank"]):
            intent = "KYC"
            tool_calls.append({"name": ToolName.GET_BANK_ACCOUNT.value, "args": {"merchantId": csc_id}})
        elif any(k in msg_lower for k in ["refund eligibility", "eligible for refund", "can i get refund"]):
            intent = "Refund"
            if entity_id:
                tool_calls.append({"name": ToolName.REFUND_ELIGIBILITY.value, "args": {"txnId": entity_id}})
            else:
                confidence = 0.6
        elif any(k in msg_lower for k in ["settlement", "last settlement"]) or (is_explicit and not any(k in msg_lower for k in ["kyc", "bank", "ticket", "refund", "aeps", "matm", "old digipay", "old balance"])):
            intent = "Settlement"
            if entity_id:
                tool_calls.append({"name": ToolName.GET_SETTLEMENT_STATUS.value, "args": {"txnId": entity_id}})
            else:
                if is_explicit:
                    tool_calls.append({
                        "name": ToolName.GET_WALLET_BALANCE.value,
                        "args": {
                            "merchantId": csc_id,
                            "fromDate": from_date,
                            "toDate": to_date
                        }
                    })
                    confidence = 0.95
                else:
                    return {
                        "intent": "Settlement",
                        "confidence_score": 0.95,
                        "tool_calls": [],
                        "clarification_prompt": "Please specify the From Date and To Date (e.g., YYYY-MM-DD or DD-MM-YYYY) for which you would like to view your settlement details."
                    }
        elif any(k in msg_lower for k in ["transaction", "where is my money", "failed", "status of"]):
            intent = "Refund"
            if entity_id:
                tool_calls.append({"name": ToolName.GET_TRANSACTION.value, "args": {"txnId": entity_id}})
            else:
                confidence = 0.5
        elif any(k in msg_lower for k in ["biometric", "face auth", "fingerprint", "face rd", "rd service", "rd", "faq", "sop", "guideline", "rule"]):
            intent = "FAQ"

        return {
            "intent": intent,
            "confidence_score": confidence,
            "tool_calls": tool_calls
        }
