import os
import logging
from datetime import datetime
from typing import Dict, List, Any, TypedDict, Annotated, Optional
import operator
import re

from sqlalchemy.ext.asyncio import AsyncSession

try:
    from langgraph.graph import StateGraph, END
    from langchain_core.runnables import RunnableConfig
except ImportError:
    StateGraph = None
    END = None
    RunnableConfig = None

from app.services.tool_apis import ToolAPIs

logger = logging.getLogger("digipay.agent_service")

# 1. State Definition
class AgentState(TypedDict):
    messages: List[Dict[str, str]]  # list of {"role": "user"|"assistant"|"system", "content": "..."}
    csc_id: str                     # authenticated merchant ID
    intent: str                     # classified intent (Refund, KYC, Wallet, Settlement, Technical, FAQ, General)
    current_agent: str              # tracking current active agent (Finance, KYC, Technical, Response, etc.)
    confidence_score: float         # Agent's confidence score (0.0 to 1.0)
    tool_calls: List[Dict[str, Any]]# list of tools to invoke: {"name": "...", "args": {...}}
    tool_outcomes: List[Dict[str, Any]] # outputs of tool executions
    policy_checked: bool            # has policy engine validated the flow?
    escalate: bool                  # does this require human handoff?
    response: str                   # final response text

# 2. Hardcoded FAQ SOPs and Guidelines (Vector DB / Qdrant local RAG simulation)
SOP_DATABASE = [
    {
        "keywords": ["biometric", "face auth", "fingerprint", "face rd", "rd service"],
        "title": "Aadhaar Face RD / Biometric verification process",
        "content": "To perform biometric authentication, ensure the Aadhaar Face RD application version 1.1 or higher is installed. The device must be registered and active. Clean the camera lens, ensure proper lighting, and place the face within the designated guide box. For fingerprint capture, verify that the scanner is connected via OTG and USB debugging is enabled in Android settings."
    },
    {
        "keywords": ["aeps", "cash withdrawal", "limit", "aeps limit"],
        "title": "AePS Cash Withdrawal limits and rules",
        "content": "According to NPCI guidelines, the maximum limit for a single AePS Cash Withdrawal transaction is ₹10,000. VLEs are prohibited from split-charging or charging extra fees to customers. A maximum of 5 successful transactions are allowed per customer per day under standard banking limits."
    },
    {
        "keywords": ["kyc", "approval time", "documents"],
        "title": "KYC policy and approval timeline",
        "content": "KYC validation takes approximately 24 to 48 business hours after document submission. Merchants must submit clear scanned copies of their PAN Card and Aadhaar Card. Address proof must match the registered shop address. If rejected, check comments and re-upload correct documents."
    },
    {
        "keywords": ["refund", "failed transaction", "reversal"],
        "title": "Failed transaction refund SLA policy",
        "content": "If a transaction fails at the bank but money is debited from the customer's account, an automatic reversal is initiated. Funds are credited back to the customer's account within 24 to 48 hours for UPI, and 5 to 7 business days for AePS. If not resolved, a dispute ticket can be raised with the UTR/RRN."
    }
]

def search_faqs(query: str) -> str:
    """Simulates Vector DB semantic search using keyword matching against SOPs."""
    query_lower = query.lower()
    matches = []
    for sop in SOP_DATABASE:
        for kw in sop["keywords"]:
            if kw in query_lower:
                matches.append(f"**{sop['title']}**:\n{sop['content']}")
                break
    if matches:
        return "\n\n".join(matches)
    return "No matching internal SOP or FAQ was found in our knowledge base."

# 3. Smart Simulator for LLM reasoning when API key is missing
def simulate_llm(state: AgentState) -> Dict[str, Any]:
    """
    Decides intents and generates tool calls or text responses
    based on the state context and latest user message.
    """
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    csc_id = state["csc_id"]
    
    # Simple regex parsing for IDs
    txn_id_match = re.search(r'(CZU[A-Z0-9]+|TKT-[A-Z0-9]+)', last_msg, re.IGNORECASE)
    entity_id = txn_id_match.group(1) if txn_id_match else None
    
    # Intent Detection
    intent = "General"
    confidence = 0.95
    tool_calls = []
    
    msg_lower = last_msg.lower()
    
    if any(k in msg_lower for k in ["balance", "money in wallet", "wallet amount"]):
        intent = "Wallet"
        tool_calls.append({"name": "getWalletBalance", "args": {"merchantId": csc_id}})
    elif any(k in msg_lower for k in ["kyc", "verify profile", "account active"]):
        intent = "KYC"
        tool_calls.append({"name": "getKYCStatus", "args": {"merchantId": csc_id}})
    elif any(k in msg_lower for k in ["bank account", "account details", "linked bank"]):
        intent = "KYC"
        tool_calls.append({"name": "getBankAccount", "args": {"merchantId": csc_id}})
    elif any(k in msg_lower for k in ["refund eligibility", "eligible for refund", "can i get refund"]):
        intent = "Refund"
        if entity_id:
            tool_calls.append({"name": "refundEligibility", "args": {"txnId": entity_id}})
        else:
            confidence = 0.6
    elif any(k in msg_lower for k in ["transaction", "where is my money", "failed", "status of"]):
        intent = "Refund"
        if entity_id:
            tool_calls.append({"name": "getTransaction", "args": {"txnId": entity_id}})
        else:
            confidence = 0.5
    elif any(k in msg_lower for k in ["settlement"]):
        intent = "Settlement"
        if entity_id:
            tool_calls.append({"name": "getSettlementStatus", "args": {"txnId": entity_id}})
        else:
            confidence = 0.5
    elif any(k in msg_lower for k in ["aeps"]):
        intent = "Technical"
        if entity_id:
            tool_calls.append({"name": "getAEPSStatus", "args": {"txnId": entity_id}})
        else:
            confidence = 0.5
    elif any(k in msg_lower for k in ["matm", "microatm"]):
        intent = "Technical"
        if entity_id:
            tool_calls.append({"name": "getMATMStatus", "args": {"txnId": entity_id}})
        else:
            confidence = 0.5
    elif any(k in msg_lower for k in ["raise ticket", "dispute", "complain", "complaint"]):
        intent = "Refund"
        category = "Refund"
        if "kyc" in msg_lower:
            category = "KYC"
        elif "settlement" in msg_lower:
            category = "Settlement"
        elif "aeps" in msg_lower:
            category = "AEPS"
            
        tool_calls.append({
            "name": "raiseTicket", 
            "args": {
                "merchantId": csc_id, 
                "category": category, 
                "details": f"Dispute raised via AI agent: {last_msg}"
            }
        })
    elif any(k in msg_lower for k in ["close ticket"]):
        intent = "General"
        if entity_id:
            tool_calls.append({"name": "closeTicket", "args": {"ticketId": entity_id}})
    elif any(k in msg_lower for k in ["statement", "report"]):
        intent = "Wallet"
        # Parse Dates if available or default
        from_date = "2026-06-01"
        to_date = "2026-06-30"
        tool_calls.append({
            "name": "generateStatement",
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

# 4. LangGraph Nodes

async def intent_router_node(state: AgentState) -> Dict[str, Any]:
    """
    Step 1: Router Agent / Intent Detection.
    Determines user query intent and routes to specialized specialists.
    """
    logger.info("LangGraph Node: intent_router_node")
    
    # Try calling actual LLM here if configured (e.g. ChatOpenAI)
    # For now, we use our smart simulator
    simulation = simulate_llm(state)
    
    intent = simulation["intent"]
    confidence = simulation["confidence_score"]
    
    # Map intent to specialist agent
    if intent in ["Wallet", "Refund", "Settlement"]:
        current_agent = "FinanceAgent"
    elif intent == "KYC":
        current_agent = "KYCAgent"
    elif intent == "Technical":
        current_agent = "TechnicalAgent"
    elif intent == "FAQ":
        current_agent = "FAQAgent"
    else:
        current_agent = "GeneralAgent"
        
    return {
        "intent": intent,
        "confidence_score": confidence,
        "current_agent": current_agent,
        "tool_calls": simulation["tool_calls"]
    }

async def finance_agent_node(state: AgentState) -> Dict[str, Any]:
    """Finance specialist node."""
    logger.info("LangGraph Node: finance_agent_node")
    return {"current_agent": "FinanceAgent"}

async def kyc_agent_node(state: AgentState) -> Dict[str, Any]:
    """KYC specialist node."""
    logger.info("LangGraph Node: kyc_agent_node")
    return {"current_agent": "KYCAgent"}

async def technical_agent_node(state: AgentState) -> Dict[str, Any]:
    """Technical support specialist node."""
    logger.info("LangGraph Node: technical_agent_node")
    return {"current_agent": "TechnicalAgent"}

async def faq_agent_node(state: AgentState) -> Dict[str, Any]:
    """FAQ search specialist node."""
    logger.info("LangGraph Node: faq_agent_node")
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    faq_content = search_faqs(last_msg)
    
    # Contextual verification prefix
    context_prefix = ""
    aadhaar_match = re.search(r'\b\d{12}\b|\b\d{4}\s\d{4}\s\d{4}\b', last_msg)
    mobile_match = re.search(r'\b\d{10}\b', last_msg)
    
    parts = []
    if aadhaar_match:
        parts.append(f"Aadhaar {aadhaar_match.group(0)}")
    if mobile_match:
        parts.append(f"mobile {mobile_match.group(0)}")
        
    if parts:
        context_prefix = f"Verified search context for {' and '.join(parts)}. "
        
    return {
        "current_agent": "FAQAgent",
        "response": context_prefix + faq_content
    }

async def tool_executor_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Executes tools that were selected by the specialists.
    This guarantees that database operations run only through verified APIs.
    """
    logger.info("LangGraph Node: tool_executor_node")
    db: AsyncSession = config.get("configurable", {}).get("db")
    if not db:
        raise ValueError("Database session missing in configurable context.")
        
    tool_calls = state.get("tool_calls", [])
    outcomes = []
    
    for tool in tool_calls:
        name = tool["name"]
        args = tool["args"]
        logger.info(f"Executing tool {name} with args: {args}")
        try:
            if name == "getTransaction":
                res = await ToolAPIs.get_transaction(db, args["txnId"])
            elif name == "getWalletBalance":
                res = await ToolAPIs.get_wallet_balance(db, args["merchantId"])
            elif name == "getKYCStatus":
                res = await ToolAPIs.get_kyc_status(db, args["merchantId"])
            elif name == "getSettlementStatus":
                res = await ToolAPIs.get_settlement_status(db, args["txnId"])
            elif name == "getBankAccount":
                res = await ToolAPIs.get_bank_account(db, args["merchantId"])
            elif name == "getMerchant":
                res = await ToolAPIs.get_merchant(db, args["merchantId"])
            elif name == "getAEPSStatus":
                res = await ToolAPIs.get_aeps_status(db, args["txnId"])
            elif name == "getMATMStatus":
                res = await ToolAPIs.get_matm_status(db, args["txnId"])
            elif name == "raiseTicket":
                res = await ToolAPIs.raise_ticket(db, args["merchantId"], args["category"], args["details"])
            elif name == "closeTicket":
                res = await ToolAPIs.close_ticket(db, args["ticketId"])
            elif name == "refundEligibility":
                res = await ToolAPIs.check_refund_eligibility(db, args["txnId"])
            elif name == "generateStatement":
                res = await ToolAPIs.generate_statement(db, args["merchantId"], args["fromDate"], args["toDate"])
            else:
                res = {"error": f"Tool '{name}' is not recognized."}
            outcomes.append({"tool": name, "status": "SUCCESS", "result": res})
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            outcomes.append({"tool": name, "status": "ERROR", "error": str(e)})
            
    return {"tool_outcomes": outcomes, "tool_calls": []}

async def validation_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Step 5: Validation / Policy Agent (RBAC + Compliance Check).
    Verifies that tool outputs conform to policies and checks RBAC.
    """
    logger.info("LangGraph Node: validation_agent_node")
    outcomes = state.get("tool_outcomes", [])
    csc_id = state["csc_id"]
    
    escalate = False
    validated_outcomes = []
    
    for item in outcomes:
        if item["status"] == "ERROR":
            logger.warning(f"Tool execution failed: {item.get('error')}")
            # If tool execution failed, we flag for human escalation
            escalate = True
            validated_outcomes.append(item)
            continue
            
        res = item.get("result", {})
        
        # Policy Check: Ensure merchant is only checking their own data
        # Check merchantId/user_id in results
        result_merchant = res.get("merchantId") or res.get("user_id") or res.get("cscId")
        
        if result_merchant and str(result_merchant) != str(csc_id):
            logger.error(f"Security Alert: Authenticated merchant {csc_id} attempted to access data for {result_merchant}!")
            validated_outcomes.append({
                "tool": item["tool"],
                "status": "SECURITY_BLOCKED",
                "error": "Access Denied: Attempted to access data belonging to a different merchant context."
            })
            escalate = True
            continue
            
        validated_outcomes.append(item)
        
    return {
        "tool_outcomes": validated_outcomes,
        "policy_checked": True,
        "escalate": escalate
    }

async def response_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Step 6: Response / PII Redaction Agent.
    Generates natural language response and redacts PII.
    """
    logger.info("LangGraph Node: response_agent_node")
    
    # If FAQ agent already compiled a text response, use it
    if state["current_agent"] == "FAQAgent" and state.get("response"):
        return {"response": mask_pii(state["response"])}
        
    # Generate final answer based on tool outputs
    outcomes = state.get("tool_outcomes", [])
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    
    if state.get("escalate"):
        response = (
            "I encountered an issue retrieving your account details, or this action requires higher authorization. "
            "I have raised this issue to our Level-2/3 human support team. An engineer will review it shortly. "
            "No further action is required from your side."
        )
        return {"response": response}
        
    if not outcomes:
        # Fallback if no tools were called and it's not a FAQ
        if state["confidence_score"] < 0.6:
            response = (
                "I'm sorry, I'm not completely sure how to assist with that transaction or request. "
                "Would you like me to connect you with a live support representative?"
            )
        else:
            response = (
                "Hello! I am your DigiPay AI Support Assistant. I can help check transaction statuses, "
                "wallet balances, KYC statuses, bank accounts, or raise dispute tickets. How can I help you today?"
            )
        return {"response": response}
        
    # Standard fintech response formatting
    lines = []
    for item in outcomes:
        tool_name = item["tool"]
        res = item.get("result", {})
        
        if item["status"] == "SECURITY_BLOCKED":
            lines.append(f"Security Policy Block: {item['error']}")
            continue
            
        if tool_name == "getWalletBalance":
            lines.append(
                f"Your active wallet balance is ₹{res['balance']:.2f}. "
                f"Your blocked balance is ₹{res['blockedBalance']:.2f}. "
                f"Your last settlement was processed on {res['lastSettlementDate'] or 'N/A'} for ₹{res['lastSettlementAmount']:.2f}."
            )
        elif tool_name == "getKYCStatus":
            status = res["status"]
            comments = res["comments"] or ""
            if status == "APPROVED":
                lines.append(f"Your KYC is fully APPROVED. Your account is active and compliant.")
            elif status == "REJECTED":
                lines.append(f"Your KYC was REJECTED. Reason: {comments}. Please re-submit valid documents.")
            else:
                lines.append(f"Your KYC status is currently PENDING. It usually takes 24-48 business hours to process.")
        elif tool_name == "getBankAccount":
            lines.append(
                f"Your linked bank account is {res['bankName']}. "
                f"Account Number: {res['bankAccountNo']}, IFSC: {res['bankIfsc']}."
            )
        elif tool_name == "getTransaction":
            status = res["status"]
            amt = res["amount"]
            date_str = res["date"] or "N/A"
            if status == "SUCCESS":
                lines.append(
                    f"Transaction {res['txnId']} of ₹{amt:.2f} was successful on {date_str}. "
                    f"UTR: {res['utr'] or 'N/A'}."
                )
            elif status == "FAILED":
                reason = res["failureReason"]
                settlement_status = res["settlementStatus"]
                reversal_msg = ""
                if settlement_status == "auto-reversal-initiated":
                    reversal_msg = " An automatic reversal has already been initiated and should credit back to the bank account shortly (typically within 20 minutes)."
                lines.append(
                    f"Transaction {res['txnId']} of ₹{amt:.2f} failed on {date_str} due to: {reason}.{reversal_msg}"
                )
            else:
                lines.append(f"Transaction {res['txnId']} status is {status}. Amount: ₹{amt:.2f}.")
        elif tool_name == "getSettlementStatus":
            status = res["status"]
            utr = res["utr"] or "N/A"
            date_str = res["settlementDate"] or "N/A"
            if status == "processed":
                lines.append(f"Settlement for your transaction is processed successfully on {date_str}. UTR: {utr}.")
            elif status == "auto-reversal-initiated":
                lines.append(f"Settlement failed. Auto-reversal is initiated with UTR {utr}. Reversal ETA: 20 minutes.")
            else:
                lines.append(f"Settlement status is {status}. Details: {res['failureReason'] or 'In progress'}.")
        elif tool_name == "raiseTicket":
            lines.append(
                f"I have raised a support ticket for your issue. "
                f"Ticket ID: {res['ticketId']} (Category: {res['category']}). Our Level-2 team will investigate immediately."
            )
        elif tool_name == "closeTicket":
            lines.append(f"Ticket {res['ticketId']} has been successfully CLOSED on {res['closedAt']}.")
        elif tool_name == "refundEligibility":
            eligible = res["eligible"]
            amt = res["amount"]
            if eligible:
                lines.append(
                    f"Transaction {res['txnId']} of ₹{amt:.2f} is ELIGIBLE for refund. "
                    f"You can request a reversal or raise a dispute ticket to trigger credit."
                )
            else:
                reasons = ", ".join(res["reasons"])
                lines.append(f"Transaction {res['txnId']} is NOT eligible for refund. Reason: {reasons}")
        elif tool_name == "generateStatement":
            lines.append(
                f"Your account statement from {res['fromDate']} to {res['toDate']} has been compiled. "
                f"It contains {res['totalTransactions']} transactions with a volume of ₹{res['totalVolume']:.2f}. "
                f"You can download it here: [Statement PDF]({res['downloadUrl']})."
            )
        else:
            lines.append(str(res))
            
    final_response = " ".join(lines)
    
    # Run PII Redaction
    final_response = mask_pii(final_response)
    
    return {"response": final_response}

# 5. PII Masking Engine
def mask_pii(text: str) -> str:
    """Mask sensitive parameters such as Aadhaar cards (12 digits) or Mobile numbers."""
    if not text:
        return text
        
    # Mask Aadhaar numbers (e.g. 12 digits: XXXX XXXX 1234 or simply 12 digits raw)
    # Match any 12 digit string or standard spaces
    aadhaar_pattern = r'\b\d{4}\s?\d{4}\s?(\d{4})\b'
    text = re.sub(aadhaar_pattern, r'XXXX XXXX \1', text)
    
    # Mask mobile numbers (e.g. 10 digits mobile, keeping only last 3 digits)
    mobile_pattern = r'\b\d{7}(\d{3})\b'
    text = re.sub(mobile_pattern, r'XXXXXXX\1', text)
    
    return text

# 6. Routing Decision Logic
def route_after_agent(state: AgentState) -> str:
    """Determines whether to call tool executor or go to response agent directly."""
    if state.get("tool_calls"):
        return "tool_executor"
    elif state["current_agent"] == "FAQAgent":
        return "response_agent"
    else:
        return "validation_agent"

# 7. Construct LangGraph Workflow
graph = None
if StateGraph is not None:
    try:
        workflow = StateGraph(AgentState)

        # Add Nodes
        workflow.add_node("intent_router", intent_router_node)
        workflow.add_node("finance_agent", finance_agent_node)
        workflow.add_node("kyc_agent", kyc_agent_node)
        workflow.add_node("technical_agent", technical_agent_node)
        workflow.add_node("faq_agent", faq_agent_node)
        workflow.add_node("tool_executor", tool_executor_node)
        workflow.add_node("validation_agent", validation_agent_node)
        workflow.add_node("response_agent", response_agent_node)

        # Set Entry Point
        workflow.set_entry_point("intent_router")

        # Define Transitions
        workflow.add_conditional_edges(
            "intent_router",
            lambda s: s["current_agent"],
            {
                "FinanceAgent": "finance_agent",
                "KYCAgent": "kyc_agent",
                "TechnicalAgent": "technical_agent",
                "FAQAgent": "faq_agent",
                "GeneralAgent": "response_agent"
            }
        )

        # Route specialized agents to tool executor or validation
        workflow.add_conditional_edges("finance_agent", route_after_agent, {"tool_executor": "tool_executor", "validation_agent": "validation_agent", "response_agent": "response_agent"})
        workflow.add_conditional_edges("kyc_agent", route_after_agent, {"tool_executor": "tool_executor", "validation_agent": "validation_agent", "response_agent": "response_agent"})
        workflow.add_conditional_edges("technical_agent", route_after_agent, {"tool_executor": "tool_executor", "validation_agent": "validation_agent", "response_agent": "response_agent"})
        workflow.add_edge("faq_agent", "response_agent")

        workflow.add_edge("tool_executor", "validation_agent")
        workflow.add_edge("validation_agent", "response_agent")
        workflow.add_edge("response_agent", END)

        # Compile Graph
        graph = workflow.compile()
    except Exception as e:
        logger.warning(f"Failed to compile LangGraph state machine: {e}. Falling back to sequential execution.")
        graph = None


class AgentOrchestrator:
    @staticmethod
    async def chat(db: AsyncSession, session_id: str, message: str, csc_id: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Executes a single chat conversation through the LangGraph agent state machine.
        """
        history_list = history or []
        
        # Build initial state
        state = {
            "messages": history_list + [{"role": "user", "content": message}],
            "csc_id": csc_id,
            "intent": "",
            "current_agent": "",
            "confidence_score": 1.0,
            "tool_calls": [],
            "tool_outcomes": [],
            "policy_checked": False,
            "escalate": False,
            "response": ""
        }
        
        config = {"configurable": {"db": db, "thread_id": session_id}}

        if graph is not None:
            final_state = await graph.ainvoke(state, config)
        else:
            # Fallback sequential orchestrator execution
            state.update(await intent_router_node(state))
            agent_name = state.get("current_agent")
            if agent_name == "FinanceAgent":
                state.update(await finance_agent_node(state))
            elif agent_name == "KYCAgent":
                state.update(await kyc_agent_node(state))
            elif agent_name == "TechnicalAgent":
                state.update(await technical_agent_node(state))
            elif agent_name == "FAQAgent":
                state.update(await faq_agent_node(state))
            
            if state.get("tool_calls"):
                state.update(await tool_executor_node(state, config))
            
            if agent_name != "FAQAgent" and agent_name != "GeneralAgent":
                state.update(await validation_agent_node(state))
                
            state.update(await response_agent_node(state))
            final_state = state

        # Log audit entry
        logger.info(
            f"AUDIT LOG | Session: {session_id} | Merchant: {csc_id} | Message: {message} | "
            f"Intent: {final_state['intent']} | Escalated: {final_state['escalate']} | "
            f"Policy Checked: {final_state['policy_checked']}"
        )
        
        return {
            "response": final_state["response"],
            "intent": final_state["intent"],
            "escalate": final_state["escalate"],
            "confidence_score": final_state["confidence_score"],
            "policy_checked": final_state["policy_checked"]
        }
