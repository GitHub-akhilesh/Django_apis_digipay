import logging
from typing import Dict, List, Any, TypedDict, Optional
from langgraph.graph import StateGraph, END
from memory.session import session_metadata_memory

# Import decomposed nodes
from workflow.nodes.classify import intent_router_node
from workflow.nodes.plan import planner_node
from workflow.nodes.execute import tool_executor_node, validation_agent_node
from workflow.nodes.respond import faq_agent_node, response_agent_node

logger = logging.getLogger("ai_platform.workflow.graph")

class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    csc_id: str
    user_roles: List[str]
    intent: str
    confidence_score: float
    tool_calls: List[Dict[str, Any]]
    tool_outcomes: List[Dict[str, Any]]
    plan_steps: List[Dict[str, Any]]
    plan_outcomes: List[Dict[str, Any]]
    awaiting_confirmation: bool
    policy_checked: bool
    escalate: bool
    response: str

# Routing after classification & planning
def route_after_planning(state: AgentState) -> str:
    if state["intent"] == "FAQ":
        return "faq_agent"
    elif state.get("awaiting_confirmation"):
        return "response_agent"
    elif not state.get("plan_steps"):
        return "validation_agent"
    return "tool_executor"

# Routing after validation
def route_after_validation(state: AgentState) -> str:
    if state.get("awaiting_confirmation"):
        return "response_agent"
    # If there are still remaining plan steps, execution loop back
    if state.get("plan_steps"):
        logger.info(f"Looping back: {len(state['plan_steps'])} steps remaining.")
        return "tool_executor"
    return "response_agent"

# Build Workflow Graph
workflow = StateGraph(AgentState)
workflow.add_node("intent_router", intent_router_node)
workflow.add_node("planner", planner_node)
workflow.add_node("tool_executor", tool_executor_node)
workflow.add_node("validation_agent", validation_agent_node)
workflow.add_node("faq_agent", faq_agent_node)
workflow.add_node("response_agent", response_agent_node)

workflow.set_entry_point("intent_router")
workflow.add_edge("intent_router", "planner")

workflow.add_conditional_edges(
    "planner",
    route_after_planning,
    {
        "faq_agent": "faq_agent",
        "response_agent": "response_agent",
        "validation_agent": "validation_agent",
        "tool_executor": "tool_executor"
    }
)

workflow.add_edge("tool_executor", "validation_agent")

workflow.add_conditional_edges(
    "validation_agent",
    route_after_validation,
    {
        "tool_executor": "tool_executor",
        "response_agent": "response_agent"
    }
)

workflow.add_edge("faq_agent", "response_agent")
workflow.add_edge("response_agent", END)

graph = workflow.compile()

from security.prompt_guard import prompt_guard
from security.input_filter import pii_input_filter
from security.output_filter import output_validation_guard

class AgentOrchestrator:
    @staticmethod
    async def chat(
        session_id: str,
        message: str,
        csc_id: str,
        history: List[Dict[str, str]],
        user_roles: List[str] = None,
        jwt_token: str = None
    ) -> Dict[str, Any]:
        # 1. Prompt Injection Validation
        prompt_guard.validate_prompt(message)
        
        # 2. PII Masking
        masked_message, restore_map = pii_input_filter.mask_pii(message)

        # Retrieve plan from metadata memory
        metadata = session_metadata_memory.get_metadata(session_id)
        plan_steps = metadata.get("plan_steps", [])
        plan_outcomes = metadata.get("plan_outcomes", [])
        awaiting_confirmation = metadata.get("awaiting_confirmation", False)
        
        # If user initiates a new topic (not confirming), we clear the previous plan state
        if message.strip().upper() != "CONFIRM" and awaiting_confirmation:
            logger.info("New message received during pending confirmation. Clearing old plan state.")
            plan_steps = []
            plan_outcomes = []
            awaiting_confirmation = False

        state = {
            "messages": history + [{"role": "user", "content": masked_message}],
            "csc_id": csc_id,
            "user_roles": user_roles or ["ROLE_MERCHANT"],
            "intent": "",
            "confidence_score": 1.0,
            "tool_calls": [],
            "tool_outcomes": [],
            "plan_steps": plan_steps,
            "plan_outcomes": plan_outcomes,
            "awaiting_confirmation": awaiting_confirmation,
            "policy_checked": False,
            "escalate": False,
            "response": ""
        }
        
        import time
        start_time = time.time()
        config = {"configurable": {"thread_id": session_id, "jwt_token": jwt_token}}
        final_state = await graph.ainvoke(state, config)
        exec_time = round((time.time() - start_time) * 1000, 2)
        
        # Persist plan state back to memory
        session_metadata_memory.save_metadata(session_id, {
            "plan_steps": final_state.get("plan_steps", []),
            "plan_outcomes": final_state.get("plan_outcomes", []),
            "awaiting_confirmation": final_state.get("awaiting_confirmation", False)
        })
        
        outcomes = final_state.get("plan_outcomes", [])
        selected_tools = [x.get("tool") for x in outcomes if x.get("tool")]
        
        explainability = {
            "intent": final_state["intent"],
            "selectedTools": selected_tools,
            "reason": f"Routed {final_state['intent']} query and executed {len(selected_tools)} tools.",
            "memoryUsed": len(history) > 0,
            "ragUsed": final_state["intent"] == "FAQ",
            "executionTimeMs": exec_time
        }

        # 3. Restore PII and validate output
        restored_response = pii_input_filter.restore_pii(final_state["response"], restore_map)
        final_response = output_validation_guard.sanitize_output(restored_response)

        return {
            "response": final_response,
            "intent": final_state["intent"],
            "escalate": final_state["escalate"],
            "policy_checked": final_state["policy_checked"],
            "explainability": explainability
        }
