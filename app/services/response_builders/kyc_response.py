from typing import Dict, Any

class KYCResponseBuilder:
    @staticmethod
    def format_kyc_status(res: Dict[str, Any]) -> str:
        status = res.get("status")
        comments = res.get("comments") or ""
        if status == "APPROVED":
            return "Your KYC is fully APPROVED. Your account is active and compliant."
        elif status == "REJECTED":
            return f"Your KYC was REJECTED. Reason: {comments}. Please re-submit valid documents."
        return "Your KYC status is currently PENDING. It usually takes 24-48 business hours to process."

    @staticmethod
    def format_bank_account(res: Dict[str, Any]) -> str:
        return f"Your linked bank account is {res.get('bankName')}. Account Number: {res.get('bankAccountNo')}, IFSC: {res.get('bankIfsc')}."
