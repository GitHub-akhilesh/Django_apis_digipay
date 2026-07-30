import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, TypedDict
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
try:
    from langgraph.graph import StateGraph, END
    from langchain_core.runnables import RunnableConfig
except ImportError:  # langgraph is optional; see _run_graph_fallback below
    StateGraph = None
    END = None
    RunnableConfig = None

from app.schemas.enums import ToolName
from app.services.tools import (
    WalletTool, TransactionTool, SettlementTool,
    KYCTool, MerchantTool, TicketTool, ReportTool
)
from app.services.intent_classifier import IntentClassifier
from app.services.response_builders import ResponseBuilderRegistry
from app.services.audit_service import AuditService
from app.utils.helpers import mask_pii

logger = logging.getLogger("digipay")

# 1. Define Agent Graph State
class AgentState(TypedDict):
    session_id: str
    csc_id: str
    messages: List[Dict[str, str]]
    intent: Optional[str]
    confidence_score: float
    current_agent: Optional[str]
    tool_calls: List[Dict[str, Any]]
    tool_outcomes: List[Dict[str, Any]]
    policy_checked: bool
    escalate: bool
    response: Optional[str]

# 2. LLM Simulation Engine for Intent Classification
def simulate_llm(state: AgentState) -> Dict[str, Any]:
    messages = state.get("messages", [])
    last_msg = messages[-1]["content"] if messages else ""
    csc_id = state.get("csc_id", "")
    return IntentClassifier.classify_intent(last_msg, csc_id)

# 3. Named Async Tool Handlers for Clean Stack Traces
async def _exec_get_transaction(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await TransactionTool.get_transaction(db, args["txnId"])

async def _exec_get_wallet_balance(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await WalletTool.get_wallet_balance(
        db,
        args["merchantId"],
        fromDate=args.get("fromDate"),
        toDate=args.get("toDate")
    )

async def _exec_get_old_digipay_balance(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await WalletTool.get_old_digipay_balance(db, args["merchantId"])

async def _exec_get_daywise_report(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await ReportTool.get_daywise_report(db, args["merchantId"], args.get("yearMonth"), args.get("day"))

async def _exec_get_txn_logs(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await TransactionTool.get_txn_logs(db, args["merchantId"], args.get("fromDate"), args.get("toDate"))

async def _exec_get_kyc_status(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await KYCTool.get_kyc_status(db, args["merchantId"])

async def _exec_get_settlement_status(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await SettlementTool.get_settlement_status(db, args["txnId"])

async def _exec_get_bank_account(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await MerchantTool.get_bank_account(db, args["merchantId"])

async def _exec_get_merchant(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await MerchantTool.get_merchant(db, args["merchantId"])

async def _exec_get_aeps_status(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await ReportTool.get_aeps_status(db, args["txnId"])

async def _exec_get_matm_status(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await ReportTool.get_matm_status(db, args["txnId"])

async def _exec_raise_ticket(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await TicketTool.raise_ticket(db, args["merchantId"], args["category"], args["details"])

async def _exec_close_ticket(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await TicketTool.close_ticket(db, args["ticketId"])

async def _exec_refund_eligibility(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await TransactionTool.check_refund_eligibility(db, args["txnId"])

async def _exec_generate_statement(db: AsyncSession, args: Dict[str, Any]) -> Dict[str, Any]:
    return await TransactionTool.generate_statement(db, args["merchantId"], args.get("fromDate"), args.get("toDate"))

TOOL_DISPATCHER = {
    ToolName.GET_TRANSACTION.value: _exec_get_transaction,
    ToolName.GET_WALLET_BALANCE.value: _exec_get_wallet_balance,
    ToolName.GET_OLD_DIGIPAY_BALANCE.value: _exec_get_old_digipay_balance,
    ToolName.GET_DAYWISE_REPORT.value: _exec_get_daywise_report,
    ToolName.GET_TXN_LOGS.value: _exec_get_txn_logs,
    ToolName.GET_KYC_STATUS.value: _exec_get_kyc_status,
    ToolName.GET_SETTLEMENT_STATUS.value: _exec_get_settlement_status,
    ToolName.GET_BANK_ACCOUNT.value: _exec_get_bank_account,
    ToolName.GET_MERCHANT.value: _exec_get_merchant,
    ToolName.GET_AEPS_STATUS.value: _exec_get_aeps_status,
    ToolName.GET_MATM_STATUS.value: _exec_get_matm_status,
    ToolName.RAISE_TICKET.value: _exec_raise_ticket,
    ToolName.CLOSE_TICKET.value: _exec_close_ticket,
    ToolName.REFUND_ELIGIBILITY.value: _exec_refund_eligibility,
    ToolName.GENERATE_STATEMENT.value: _exec_generate_statement,
}

# 4. LangGraph Nodes

async def intent_router_node(state: AgentState) -> Dict[str, Any]:
    """Step 1: Router Agent / Intent Detection."""
    logger.info("LangGraph Node: intent_router_node")
    simulation = simulate_llm(state)
    intent = simulation["intent"]
    confidence = simulation["confidence_score"]
    
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
        
    res = {
        "intent": intent,
        "confidence_score": confidence,
        "current_agent": current_agent,
        "tool_calls": simulation.get("tool_calls", [])
    }
    if simulation.get("clarification_prompt"):
        res["response"] = simulation["clarification_prompt"]
    return res

async def specialist_agent_node(state: AgentState) -> Dict[str, Any]:
    """Step 2 & 3: Specialist Agent."""
    agent_name = state["current_agent"]
    logger.info(f"LangGraph Node: specialist_agent_node ({agent_name})")
    return {}

async def faq_agent_node(state: AgentState) -> Dict[str, Any]:
    """Step 3b: Knowledge RAG / FAQ Specialist Agent."""
    logger.info("LangGraph Node: faq_agent_node (RAG lookup)")
    messages = state.get("messages", [])
    last_msg = messages[-1]["content"] if messages else ""
    
    faq_content = (
        "For DigiPay AePS & Face Authentication, please ensure your Registered Device (RD) service "
        "is updated to v2.0+ and biometric drivers are active. For microATM (mATM), pair your Bluetooth "
        "pinpad before initiating transaction."
    )
    
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
    """Step 4: Tool Executor Node."""
    logger.info("LangGraph Node: tool_executor_node")
    db: AsyncSession = config.get("configurable", {}).get("db")
    if not db:
        raise ValueError("Database session missing in configurable context.")
        
    tool_calls = state.get("tool_calls", [])
    outcomes = []
    csc_id = state.get("csc_id", "")
    
    for tool in tool_calls:
        name = tool["name"]
        args = tool["args"]
        logger.info(f"Executing tool {name} with args: {args}")
        try:
            handler = TOOL_DISPATCHER.get(name)
            if handler:
                res = await handler(db, args)
                status = "SUCCESS"
            else:
                res = {"error": f"Tool '{name}' is not recognized."}
                status = "ERROR"
            outcomes.append({"tool": name, "status": status, "result": res})
            AuditService.log_tool_execution(csc_id, name, args, status)
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            outcomes.append({"tool": name, "status": "ERROR", "error": str(e)})
            AuditService.log_tool_execution(csc_id, name, args, "ERROR")
            
    return {"tool_outcomes": outcomes, "tool_calls": []}

async def validation_agent_node(state: AgentState) -> Dict[str, Any]:
    """Step 5: Validation / Policy Agent (RBAC + Compliance Check)."""
    logger.info("LangGraph Node: validation_agent_node")
    outcomes = state.get("tool_outcomes", [])
    csc_id = state["csc_id"]
    
    escalate = False
    validated_outcomes = []
    
    for item in outcomes:
        if item["status"] == "ERROR":
            logger.warning(f"Tool execution failed: {item.get('error')}")
            escalate = True
            validated_outcomes.append(item)
            continue
            
        res = item.get("result", {})
        result_merchant = res.get("merchantId") or res.get("user_id") or res.get("cscId")
        
        if result_merchant and str(result_merchant) != str(csc_id):
            logger.error(f"Security Alert: Authenticated merchant {csc_id} attempted to access data for {result_merchant}!")
            AuditService.log_security_event(csc_id, "RBAC_VIOLATION", f"Attempted access to merchant {result_merchant}")
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
    """Step 6: Response / PII Redaction Agent."""
    logger.info("LangGraph Node: response_agent_node")
    
    if state["current_agent"] == "FAQAgent" and state.get("response"):
        return {"response": mask_pii(state["response"])}
        
    outcomes = state.get("tool_outcomes", [])
    
    if state.get("escalate"):
        response = (
            "I encountered an issue retrieving your account details, or this action requires higher authorization. "
            "I have raised this issue to our Level-2/3 human support team. An engineer will review it shortly. "
            "No further action is required from your side."
        )
        return {"response": response}
        
    if not outcomes:
        if state.get("response"):
            return {"response": mask_pii(state["response"])}
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
        
    lines = []
    for item in outcomes:
        tool_name = item["tool"]
        res = item.get("result", {})
        
        if item["status"] == "SECURITY_BLOCKED":
            lines.append(f"Security Policy Block: {item['error']}")
            continue
            
        formatted_text = ResponseBuilderRegistry.format_response(tool_name, res, intent=state.get("intent"))
        lines.append(formatted_text)
        
    final_response = " ".join(lines)
    return {"response": mask_pii(final_response)}

def route_next_node(state: AgentState) -> str:
    current_agent = state["current_agent"]
    if current_agent == "FAQAgent":
        return "faq_agent"
    return "specialist_agent"

def route_after_specialist(state: AgentState) -> str:
    if state.get("tool_calls"):
        return "tool_executor"
    return "response_agent"

# 5. Build Graph
def build_agent_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("specialist_agent", specialist_agent_node)
    workflow.add_node("faq_agent", faq_agent_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("validation_agent", validation_agent_node)
    workflow.add_node("response_agent", response_agent_node)
    
    workflow.set_entry_point("intent_router")
    
    workflow.add_conditional_edges("intent_router", route_next_node, {
        "faq_agent": "faq_agent",
        "specialist_agent": "specialist_agent"
    })
    
    workflow.add_edge("faq_agent", "response_agent")
    
    workflow.add_conditional_edges("specialist_agent", route_after_specialist, {
        "tool_executor": "tool_executor",
        "response_agent": "response_agent"
    })
    
    workflow.add_edge("tool_executor", "validation_agent")
    workflow.add_edge("validation_agent", "response_agent")
    workflow.add_edge("response_agent", END)
    
    return workflow.compile()

agent_app = build_agent_graph() if StateGraph is not None else None


async def _run_graph_fallback(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the same nodes and routing as build_agent_graph(), without langgraph.

    AgentState declares no reducers, so langgraph merges each node's partial
    return by overwrite -- which is exactly what dict.update() does here.
    """
    async def step(node, *args):
        result = await node(*args)
        if result:
            state.update(result)

    await step(intent_router_node, state)

    if route_next_node(state) == "faq_agent":
        await step(faq_agent_node, state)
    else:
        await step(specialist_agent_node, state)
        if route_after_specialist(state) == "tool_executor":
            await step(tool_executor_node, state, config)
            await step(validation_agent_node, state)

    await step(response_agent_node, state)
    return state


class AgentOrchestrator:
    """Orchestrator for managing AI Chat sessions using LangGraph."""
    
    @staticmethod
    async def chat(
        db: AsyncSession,
        session_id: str,
        message: str,
        csc_id: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        logger.info(f"AgentOrchestrator.chat session={session_id}, csc_id={csc_id}")
        
        messages = list(history) if history else []
        messages.append({"role": "user", "content": message})
        
        initial_state: AgentState = {
            "session_id": session_id,
            "csc_id": csc_id,
            "messages": messages,
            "intent": None,
            "confidence_score": 1.0,
            "current_agent": None,
            "tool_calls": [],
            "tool_outcomes": [],
            "policy_checked": False,
            "escalate": False,
            "response": None
        }
        
        config = {"configurable": {"db": db, "thread_id": session_id}}
        if agent_app is not None:
            final_state = await agent_app.ainvoke(initial_state, config=config)
        else:
            final_state = await _run_graph_fallback(dict(initial_state), config)
        
        return {
            "status": "OK",
            "response": final_state.get("response", "Thank you for using DigiPay AI Support."),
            "intent": final_state.get("intent", "General"),
            "escalate": final_state.get("escalate", False),
            "confidenceScore": final_state.get("confidence_score", 1.0),
            "confidence_score": final_state.get("confidence_score", 1.0),
            "policyChecked": final_state.get("policy_checked", True),
            "policy_checked": final_state.get("policy_checked", True)
        }
