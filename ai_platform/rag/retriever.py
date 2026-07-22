import logging
import re
from typing import List, Dict

logger = logging.getLogger("ai_platform.rag.retriever")

# Local SOP Knowledge Base
SOP_DATABASE = [
    {
        "keywords": ["biometric", "face auth", "fingerprint", "face rd", "rd service"],
        "title": "Aadhaar Face RD & Fingerprint Scanner Setup Guide",
        "content": "Ensure Aadhaar Face RD (v1.1+) is installed. Clean camera lenses, verify proper front-face lighting, and keep within the guide box. USB scanners must have OTG enabled in Android Settings and USB debugging turned on. Biometric codes are audited for compliance with NPCI specifications."
    },
    {
        "keywords": ["limit", "aeps limit", "withdrawal limit", "maximum amount"],
        "title": "AePS Cash Withdrawal Transaction Limits",
        "content": "Standard AePS single transaction limit is ₹10,000. Customer daily transaction count limits are capped at 5 withdrawals. VLEs are strictly prohibited from split-charging or demanding processing fees from merchants or VLE customers."
    },
    {
        "keywords": ["kyc time", "kyc document", "verification timeline", "kyc approval"],
        "title": "KYC Approval SLA and Rejections SOP",
        "content": "KYC reviews are completed within 24-48 business hours after document uploading. PAN and Aadhaar copies must be scanned flat and clear. Names must match bank account details. Address proofs must correspond to the active merchant business site."
    },
    {
        "keywords": ["settlement time", "payout cycle", "settlement sla", "delay"],
        "title": "Merchant Wallet Payout Settlement SOP",
        "content": "Standard settlements are processed daily in batch cycles. IMPS cycles complete within 2 hours; NEFT transfers clear inside standard banking slots (Monday-Friday). If a settlement fails, funds are automatically returned to the merchant wallet balance."
    },
    {
        "keywords": ["chargeback", "dispute window", "chargeback rules"],
        "title": "NPCI Chargeback Rules and Dispute SOP",
        "content": "Chargeback complaints can be raised within 30 days from the transaction date. Merchants must submit a valid UTR, RRN, customer mobile number, and receipt. Settlement issues must contain bank statement proofs showing non-credit."
    }
]

class RAGEngine:
    @staticmethod
    def query(text: str) -> str:
        """Simulate Vector Database semantic similarity match against SOPs."""
        logger.info(f"RAG: query(text='{text}')")
        query_lower = text.lower()
        matches = []
        
        for sop in SOP_DATABASE:
            for keyword in sop["keywords"]:
                if keyword in query_lower:
                    matches.append(f"### {sop['title']}\n{sop['content']}")
                    break
                    
        if matches:
            return "\n\n".join(matches)
        return "No specific internal SOP or FAQ was found in our knowledge base."
