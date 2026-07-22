import re
import logging
import asyncio
from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from services.tool_executor import tool_executor_service

logger = logging.getLogger("ai_platform.workflow.nodes.execute")

async def tool_executor_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    logger.info("Graph Node: tool_executor")
    
    plan_steps = state.get("plan_steps", [])
    plan_outcomes = state.get("plan_outcomes", [])
    user_roles = state["user_roles"]
    jwt_token = config.get("configurable", {}).get("jwt_token")
    
    if not plan_steps:
        return {}
        
    awaiting_confirmation = False
    new_outcomes = list(plan_outcomes)
    remaining_steps = []
    
    completed_ids = {x["id"] for x in new_outcomes}
    
    ready_steps = []
    for step in plan_steps:
        deps = step.get("dependencies", [])
        if all(d in completed_ids for d in deps):
            ready_steps.append(step)
        else:
            remaining_steps.append(step)
            
    if not ready_steps:
        return {}
        
    # Check if any of the ready steps requires confirmation
    for step in ready_steps:
        if step.get("requires_confirmation"):
            logger.info(f"Halt: Step {step['id']} ({step['tool']}) requires human confirmation.")
            awaiting_confirmation = True
            
    if awaiting_confirmation:
        return {
            "awaiting_confirmation": True
        }
        
    # Execution of ready steps with parameter propagation
    for step in ready_steps:
        for dep in step.get("dependencies", []):
            parent_out = next((x for x in new_outcomes if x["id"] == dep), None)
            if parent_out and parent_out["status"] == "SUCCESS":
                parent_res = parent_out["result"]
                if isinstance(parent_res, dict):
                    if "merchantId" in parent_res and "merchantId" not in step["args"]:
                        step["args"]["merchantId"] = parent_res["merchantId"]
                    if "txnId" in parent_res and "txnId" not in step["args"]:
                        step["args"]["txnId"] = parent_res["txnId"]

    # Run parallel vs sequential
    parallel_steps = [s for s in ready_steps if s.get("parallel", True)]
    sequential_steps = [s for s in ready_steps if not s.get("parallel", True)]
    
    async def execute_one(step):
        name = step["tool"]
        args = step["args"]
        try:
            exec_res = await tool_executor_service.execute_tool(
                tool_name=name,
                args=args,
                user_roles=user_roles,
                jwt_token=jwt_token,
                caller_merchant_id=state.get("csc_id")
            )
            return {
                "id": step["id"],
                "tool": name,
                "status": "SUCCESS",
                "result": exec_res["result"],
                "cacheHit": exec_res["cacheHit"],
                "latency_ms": exec_res["latency_ms"]
            }
        except Exception as e:
            logger.error(f"Tool execution failed in step {step['id']}: {e}")
            return {
                "id": step["id"],
                "tool": name,
                "status": "ERROR",
                "error": str(e),
                "cacheHit": False,
                "latency_ms": 0.0
            }

    executed_results = []
    if parallel_steps:
        executed_results = await asyncio.gather(*(execute_one(s) for s in parallel_steps))
    
    for s in sequential_steps:
        res = await execute_one(s)
        executed_results.append(res)
        
    new_outcomes.extend(executed_results)
    
    return {
        "plan_steps": remaining_steps,
        "plan_outcomes": new_outcomes,
        "tool_outcomes": [x for x in new_outcomes if x["status"] == "SUCCESS"]
    }

async def validation_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Graph Node: validation_agent (Policy Check)")
    outcomes = state.get("plan_outcomes", [])
    csc_id = state["csc_id"]
    
    escalate = False
    validated = []
    
    for item in outcomes:
        if item["status"] == "ERROR":
            escalate = True
            validated.append(item)
            continue
            
        res = item.get("result", {})
        owner = None
        if isinstance(res, dict):
            owner = res.get("merchantId") or res.get("user_id") or res.get("cscId")
        elif isinstance(res, str):
            match = re.search(r'(?:merchant\s*|for\s*)([0-9]{12})', res.lower())
            if match:
                owner = match.group(1)
                
        if owner and str(owner) != str(csc_id):
            logger.error(f"POLICY BREACH: Merchant {csc_id} attempted to inspect record of {owner}!")
            validated.append({
                "id": item["id"],
                "tool": item["tool"],
                "status": "SECURITY_BLOCKED",
                "error": "Access Denied: Record owner mismatch."
            })
            escalate = True
            continue
            
        validated.append(item)
        
    return {
        "plan_outcomes": validated,
        "policy_checked": True,
        "escalate": escalate
    }
