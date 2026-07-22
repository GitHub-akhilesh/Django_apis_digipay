import re
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("ai_platform.llm.provider")

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        """Asynchronously invoke the model with context prompts."""
        pass

    def _simulate_response(self, prompt: str, system_instruction: str) -> str:
        prompt_lower = prompt.lower()
        
        # 4. DAG Planner Prompt
        if "planner" in prompt_lower or "dag" in prompt_lower or "decompose" in prompt_lower:
            user_msg_match = re.search(r'(?:user message|user query)\s*:\s*["\'](.*?)["\']', prompt_lower)
            user_msg = user_msg_match.group(1) if user_msg_match else prompt_lower
            
            csc_match = re.search(r'(?:csc_id|cscid|merchantid|merchant_id)\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?', prompt_lower)
            csc_id = csc_match.group(1) if csc_match else "500100100014"
            
            txn_match = re.search(r'(?:txnid|txn_id)\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?', prompt_lower)
            txn_id = txn_match.group(1).upper() if txn_match else "CZUCW178186672384906DQQOQSU69890796"
            
            steps = []
            if "balance" in user_msg or "wallet" in user_msg:
                steps.append({
                    "id": "step_1",
                    "tool": "getWalletBalance",
                    "args": {"merchantId": csc_id},
                    "dependencies": [],
                    "parallel": True,
                    "requires_confirmation": False
                })
            elif "limits" in user_msg:
                steps.append({
                    "id": "step_1",
                    "tool": "getLimits",
                    "args": {"merchantId": csc_id},
                    "dependencies": [],
                    "parallel": True,
                    "requires_confirmation": False
                })
            elif "kyc" in user_msg:
                steps.append({
                    "id": "step_1",
                    "tool": "getMerchantStatus",
                    "args": {"merchantId": csc_id},
                    "dependencies": [],
                    "parallel": True,
                    "requires_confirmation": False
                })
            elif "reversal" in user_msg or "refund" in user_msg or "reverse" in user_msg:
                steps.append({
                    "id": "step_1",
                    "tool": "getTransaction",
                    "args": {"txnId": txn_id},
                    "dependencies": [],
                    "parallel": True,
                    "requires_confirmation": False
                })
                steps.append({
                    "id": "step_2",
                    "tool": "reverseTransaction",
                    "args": {"txnId": txn_id},
                    "dependencies": ["step_1"],
                    "parallel": False,
                    "requires_confirmation": True
                })
            else:
                steps.append({
                    "id": "step_1",
                    "tool": "getMerchantProfile",
                    "args": {"merchantId": csc_id},
                    "dependencies": [],
                    "parallel": True,
                    "requires_confirmation": False
                })
                
            return json.dumps({
                "planner_confidence": 0.98,
                "steps": steps
            })

        # 1. Intent Classification Prompt
        if "classify" in prompt_lower or "intent" in prompt_lower:
            user_msg_match = re.search(r'(?:user message|user query)\s*:\s*["\'](.*?)["\']', prompt_lower)
            user_msg = user_msg_match.group(1) if user_msg_match else prompt_lower
            
            csc_match = re.search(r'(?:csc_id|cscid|merchantid|merchant_id)\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?', prompt_lower)
            csc_id = csc_match.group(1) if csc_match else "500100100014"
            
            # Extract txnId or ticketId if present
            txn_match = re.search(r'(?:txnid|txn_id|ticketid|ticket_id)\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?', prompt_lower)
            txn_id = txn_match.group(1).upper() if txn_match else "CZUCW178186672384906DQQOQSU69890796"
            
            intent = "General"
            confidence = 0.98
            tool_calls = []
            
            # Heuristics based on user_msg
            if "balance" in user_msg or "wallet" in user_msg:
                intent = "Wallet"
                tool_calls.append({"name": "getWalletBalance", "args": {"merchantId": csc_id}})
            elif "limits" in user_msg:
                intent = "Wallet"
                tool_calls.append({"name": "getLimits", "args": {"merchantId": csc_id}})
            elif "kyc" in user_msg:
                intent = "KYC"
                tool_calls.append({"name": "getKYCStatus", "args": {"merchantId": csc_id}})
            elif "bank" in user_msg:
                intent = "KYC"
                tool_calls.append({"name": "getBankAccount", "args": {"merchantId": csc_id}})
            elif "statement" in user_msg:
                intent = "Wallet"
                tool_calls.append({"name": "generateStatement", "args": {"merchantId": csc_id, "fromDate": "2026-06-01", "toDate": "2026-06-30"}})
            elif "reversal" in user_msg or "refund" in user_msg:
                intent = "Refund"
                tool_calls.append({"name": "refundEligibility", "args": {"txnId": txn_id}})
            elif "transaction" in user_msg or "status of" in user_msg:
                intent = "Refund"
                tool_calls.append({"name": "getTransaction", "args": {"txnId": txn_id}})
            elif "close ticket" in user_msg:
                intent = "General"
                tool_calls.append({"name": "closeTicket", "args": {"ticketId": txn_id}})
            elif "ticket" in user_msg or "complain" in user_msg or "dispute" in user_msg:
                intent = "Refund"
                tool_calls.append({"name": "raiseTicket", "args": {"merchantId": csc_id, "category": "Refund", "details": f"Dispute ticket raised"}})
            elif any(k in user_msg for k in ["biometric", "face auth", "fingerprint", "rd service", "limit", "faq"]):
                intent = "FAQ"

            return json.dumps({
                "intent": intent,
                "confidence": confidence,
                "tool_calls": tool_calls
            })

        # 2. Response formatting prompt
        if "outcomes" in prompt_lower or "tool outcomes" in prompt_lower or "result" in prompt_lower:
            # We check what tool results are inside the prompt
            if "getwalletbalance" in prompt_lower:
                return "Your wallet balance is ₹4560.50 (Blocked Balance: ₹120.00). Last settlement cleared on 2026-07-19 18:30:00 for ₹1480.00."
            elif "getkycstatus" in prompt_lower:
                return "Your KYC verification status is: APPROVED. Documents: PAN/Aadhaar. Review comments: Documents verified manually."
            elif "getbankaccount" in prompt_lower:
                return "Your registered settlement bank is State Bank of India. Account Number: 30091234567, IFSC: SBIN0001234."
            elif "gettransaction" in prompt_lower:
                if "failed" in prompt_lower:
                    return "Transaction CZUCW111222333444555DQQOQSU11122233 of ₹500.00 failed due to: Bank timeout. An automatic reversal has already been initiated and should credit back to the bank account shortly (typically within 20 minutes)."
                return "Transaction CZUCW178186672384906DQQOQSU69890796 of ₹1000.00 was successful on 2026-06-19 16:26:05. UTR: UTR123456789."
            elif "refundeligibility" in prompt_lower:
                if "ineligible" in prompt_lower or "not eligible" in prompt_lower:
                    return "Transaction is ineligible for refund. Reason: Transaction status is SUCCESS, not FAILED."
                return "Transaction is eligible for reversal."
            elif "raiseticket" in prompt_lower:
                return "A support ticket has been raised. Our operations team is reviewing it."
            elif "closeticket" in prompt_lower:
                return "Support ticket has been marked CLOSED."
            elif "generatestatement" in prompt_lower:
                return "Your account report is generated: [Download Statement PDF](https://api.digipay.in/statements/stmt_500100100014.pdf)."
            elif "security_blocked" in prompt_lower or "access denied" in prompt_lower:
                return "Security Warning: Access Denied: Record owner mismatch."
                
            return "Your request was processed successfully. All details have been verified."

        # 3. RAG/FAQ Prompts
        if "faq" in prompt_lower or "sop" in prompt_lower or "knowledge" in prompt_lower or "setup guide" in prompt_lower or "aadhaar face rd" in prompt_lower:
            return "Based on our SOP Guidelines: Ensure Aadhaar Face RD (v1.1+) is installed. OTG must be enabled in Settings."

        # Default fallback
        return "Hello, I am your DigiPay AI Support Assistant. How can I help you today?"
