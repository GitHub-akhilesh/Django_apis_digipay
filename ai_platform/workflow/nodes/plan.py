import logging
from typing import Any, Dict, List

from planner.service import PlannerService
from tools.registry import requires_confirmation

logger = logging.getLogger("ai_platform.workflow.nodes.plan")


def _apply_confirmation_policy(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Re-derive the confirmation requirement from the tool registry.

    The planner is asked to flag state-changing steps, but a model can forget.
    The registry is the authority, so a step naming a tool whose backing API is
    not read-only is escalated to needing confirmation regardless of what the
    plan said. This runs only when a plan is first created — the CONFIRM branch
    returns before this, so an approved plan is not re-flagged into a loop.
    """
    enforced = []
    for step in steps:
        step = {**step}
        if requires_confirmation(step.get("tool", "")):
            if not step.get("requires_confirmation"):
                logger.info(
                    "Escalating step %s (%s) to require confirmation: tool changes state.",
                    step.get("id"), step.get("tool"),
                )
            step["requires_confirmation"] = True
        enforced.append(step)
    return enforced

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
    user_roles = state.get("user_roles") or ["ROLE_MERCHANT"]
    plan = await PlannerService.create_plan(last_msg, intent, csc_id, user_roles=user_roles)
    
    steps = _apply_confirmation_policy(plan.get("steps", []))
    confidence = plan.get("planner_confidence", 1.0)

    # Check if any step requires human confirmation
    awaiting_confirmation = any(s.get("requires_confirmation") for s in steps)
    
    return {
        "plan_steps": steps,
        "awaiting_confirmation": awaiting_confirmation,
        "confidence_score": confidence
    }
