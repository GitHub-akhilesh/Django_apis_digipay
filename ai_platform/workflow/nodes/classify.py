import logging
from typing import Dict, Any
from intent.classifier import IntentClassifier

logger = logging.getLogger("ai_platform.workflow.nodes.classify")

async def intent_router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Graph Node: intent_router")
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    csc_id = state["csc_id"]
    user_roles = state.get("user_roles") or ["ROLE_MERCHANT"]

    result = await IntentClassifier.classify(last_msg, csc_id, user_roles=user_roles)
    intent = result["intent"]
    confidence = result["confidence"]
    tool_calls = result["tool_calls"]
    
    return {
        "intent": intent,
        "confidence_score": confidence,
        "tool_calls": tool_calls
    }
