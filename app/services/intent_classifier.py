import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.schemas.enums import ToolName

logger = logging.getLogger("digipay")

class IntentClassifier:
    """Intent Classification Engine combining rule-based heuristics and LLM capability."""

    @staticmethod
    def classify_intent(last_msg: str, csc_id: str) -> Dict[str, Any]:
        msg_lower = last_msg.lower()
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
        elif any(k in msg_lower for k in ["transaction", "where is my money", "failed", "status of"]):
            intent = "Refund"
            if entity_id:
                tool_calls.append({"name": ToolName.GET_TRANSACTION.value, "args": {"txnId": entity_id}})
            else:
                confidence = 0.5
        elif any(k in msg_lower for k in ["settlement"]):
            intent = "Settlement"
            if entity_id:
                tool_calls.append({"name": ToolName.GET_SETTLEMENT_STATUS.value, "args": {"txnId": entity_id}})
            else:
                confidence = 0.5
        elif any(k in msg_lower for k in ["txn logs", "transaction logs", "logs"]):
            intent = "Wallet"
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")
            tool_calls.append({
                "name": ToolName.GET_TXN_LOGS.value,
                "args": {
                    "merchantId": csc_id,
                    "fromDate": from_date,
                    "toDate": to_date
                }
            })
        elif any(k in msg_lower for k in ["statement", "report", "passbook", "history"]):
            intent = "Wallet"
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")
            tool_calls.append({
                "name": ToolName.GENERATE_STATEMENT.value,
                "args": {
                    "merchantId": csc_id,
                    "fromDate": from_date,
                    "toDate": to_date
                }
            })
        elif any(k in msg_lower for k in ["biometric", "face auth", "fingerprint", "face rd", "rd service", "rd", "faq", "sop", "guideline", "rule"]):
            intent = "FAQ"

        return {
            "intent": intent,
            "confidence_score": confidence,
            "tool_calls": tool_calls
        }
