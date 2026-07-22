from typing import Dict, Any

def route_intent(intent: str) -> str:
    """Map intent types to downstream router targets."""
    if intent in ["CHECK_BALANCE", "CHECK_LIMITS", "LEDGER_STATEMENT", "TXN_DETAILS", "TXN_REVERSAL", "PASSBOOK_VIEW"]:
        return "FinanceAgent"
    elif intent in ["MERCHANT_PROFILE", "MERCHANT_STATUS"]:
        return "KYCAgent"
    elif intent == "FAQ":
        return "FAQAgent"
    return "GeneralAgent"
