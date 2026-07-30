import json
import logging
from typing import Any, Dict, List, Optional

from llm.orchestrator import llm_orchestrator
from tools.catalog import build_tool_catalog

logger = logging.getLogger("ai_platform.planner.service")

class PlannerService:
    @staticmethod
    async def create_plan(
        message: str,
        intent: str,
        csc_id: str,
        user_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Decompose a user request into a dependency plan of tool executions.

        The supported-tool list is generated from the live registry and filtered
        to the caller's roles, so gateway APIs registered later become plannable
        without editing this prompt.
        """
        tool_catalog = build_tool_catalog(roles=user_roles)

        prompt = f"""
        You are the AI Planner for DigiPay. Decompose the user request into a series of tool execution steps.
        User message: "{message}"
        Intent: {intent}
        Context merchantId (csc_id): "{csc_id}"
        Caller roles: {user_roles or ["ROLE_MERCHANT"]}

        Supported tools, grouped by domain:
        {tool_catalog}

        Rules:
        1. Only emit steps whose tool name appears in the list above.
        2. Fill cscId and merchantId arguments from the caller context above. Never invent an
           identifier, and never target a CSC ID other than the caller's own.
        3. Dates use dd-MM-yyyy. Default to the last 30 days when the user gives no range.
        4. Any tool annotated as changing state must have "requires_confirmation": true.
        5. Set "parallel": true for steps with no dependencies.
        6. When the user has not supplied an identifier a detail tool needs, plan the matching
           listing tool first and make the detail step depend on it.
        7. If satisfying the request would require moving money, reversing or refunding a
           payment, blocking a user, registering a device, creating or deleting a record, or
           authenticating a customer, return an empty steps array — the assistant is read-only
           for those operations.

        Format output strictly as a JSON object:
        {{
          "planner_confidence": <float>,
          "steps": [
            {{
              "id": "<unique_id>",
              "tool": "<tool_name>",
              "args": {{...}},
              "dependencies": ["<dep_id>"],
              "parallel": <bool>,
              "requires_confirmation": <bool>
            }}
          ]
        }}
        
        Only return the raw JSON object. Do not include markdown code wrappers.
        """
        resp = await llm_orchestrator.generate(prompt, system_instruction="DAG Planner")
        
        try:
            clean_json = resp.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            
            data = json.loads(clean_json)
            return {
                "planner_confidence": data.get("planner_confidence", 1.0),
                "steps": data.get("steps", [])
            }
        except Exception as e:
            logger.error(f"Planner failed to parse plan JSON: {resp} - Error: {e}")
            return {
                "planner_confidence": 0.5,
                "steps": []
            }
