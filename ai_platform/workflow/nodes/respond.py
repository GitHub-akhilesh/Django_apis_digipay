import re
import json
import logging
from typing import Dict, Any
from llm.orchestrator import llm_orchestrator
from rag.hybrid_retriever import hybrid_retriever
from rag.citation_engine import citation_engine
from services.audit_service import audit_service

logger = logging.getLogger("ai_platform.workflow.nodes.respond")

async def faq_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Graph Node: faq_agent")
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    chunks = hybrid_retriever.retrieve(last_msg, intent=state.get("intent", "FAQ"))
    
    faq_content = "\n\n".join([f"### {c['source']} (Page {c['page']})\n{c['text']}" for c in chunks]) if chunks else "No documents matched."
    
    prompt = f"""
    You are a support agent. Answer the user question based on the retrieved knowledge base document.
    User Question: "{last_msg}"
    Knowledge Base Document:
    {faq_content}
    
    Provide a concise, helpful, and friendly support response.
    """
    
    response = await llm_orchestrator.generate(prompt, system_instruction="RAG Support Advisor")
    citations = citation_engine.format_citations(chunks)
    
    return {
        "response": response + citations
    }

async def response_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Graph Node: response_agent (Formatting & PII Redactor)")
    
    if state.get("awaiting_confirmation"):
        res_text = (
            "I have prepared a plan that requires your confirmation. "
            "Please review the pending steps and reply 'CONFIRM' to execute."
        )
        return {"response": res_text}
        
    if state["intent"] == "FAQ" and state.get("response"):
        return {"response": mask_pii(state["response"])}
        
    outcomes = state.get("tool_outcomes", [])
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    
    if state.get("escalate"):
        res_text = (
            "I encountered an issue verifying your query context or accessing the database details. "
            "I have flagged this for Level-2 human support. A representative will connect with you shortly."
        )
        return {"response": res_text}
        
    if not outcomes:
        if state["confidence_score"] < 0.6:
            res_text = "I'm not sure how to retrieve that information. Should I escalate this to a live agent?"
            return {"response": res_text}
        res_text = "Hello, I am your DigiPay AI Support Assistant. How can I help you today?"
        return {"response": res_text}

    prompt = f"""
    You are the response formatting agent for DigiPay AI platform.
    Construct a professional, helpful, friendly, and natural support message to the merchant based on their original query and the results returned by our backend tools.
    
    Merchant Query: "{last_msg}"
    Backend Tool Outcomes:
    {json.dumps(outcomes)}
    
    Ensure the response is structured, clear, and direct. Format cash/rupees cleanly using ₹ symbols.
    """
    
    response = await llm_orchestrator.generate(prompt, system_instruction="Response Formatter")
    masked_res = mask_pii(response)
    
    # Audit Trail Logging
    audit_service.record_interaction(
        session_id="graph_session",
        user_query=last_msg,
        intent=state["intent"],
        tools_executed=outcomes,
        llm_response=masked_res,
        csc_id=state["csc_id"],
        roles=state["user_roles"]
    )
    
    return {"response": masked_res}

def mask_pii(text: str) -> str:
    if not text:
        return text
    aadhaar_pattern = r'\b\d{4}\s?\d{4}\s?(\d{4})\b|\b\d{8}(\d{4})\b'
    text = re.sub(aadhaar_pattern, lambda m: f"XXXX XXXX {m.group(1) or m.group(2)}", text)
    mobile_pattern = r'\b\d{7}(\d{3})\b'
    text = re.sub(mobile_pattern, r'XXXXXXX\1', text)
    return text
