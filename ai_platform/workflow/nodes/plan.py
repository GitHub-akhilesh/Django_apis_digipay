import logging
from typing import Dict, Any
from planner.service import PlannerService

logger = logging.getLogger("ai_platform.workflow.nodes.plan")

async def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Graph Node: planner")
    last_msg = state["messages"][-1]["content"] if state["messages"] else ""
    
    # 1. Handle confirmation message bypass check
    if last_msg.strip().upper() == "CONFIRM" and state.get("awaiting_confirmation"):
        logger.info("User sent CONFIRM. Proceeding with pending plan.")
        updated_steps = []
        for step in state.get("plan_steps", []):
            step_copy = {**step}
            if step_copy.get("requires_confirmation"):
                step_copy["requires_confirmation"] = False
            updated_steps.append(step_copy)
            
        return {
            "plan_steps": updated_steps,
            "awaiting_confirmation": False
        }
        
    # Generate new plan
    intent = state.get("intent", "GENERAL")
    csc_id = state.get("csc_id")
    plan = await PlannerService.create_plan(last_msg, intent, csc_id)
    
    steps = plan.get("steps", [])
    confidence = plan.get("planner_confidence", 1.0)
    
    # Check if any step requires human confirmation
    awaiting_confirmation = any(s.get("requires_confirmation") for s in steps)
    
    return {
        "plan_steps": steps,
        "awaiting_confirmation": awaiting_confirmation,
        "confidence_score": confidence
    }
