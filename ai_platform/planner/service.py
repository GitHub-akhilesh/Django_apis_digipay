import json
import logging
from typing import Dict, Any, List
from llm.orchestrator import llm_orchestrator

logger = logging.getLogger("ai_platform.planner.service")

class PlannerService:
    @staticmethod
    async def create_plan(message: str, intent: str, csc_id: str) -> Dict[str, Any]:
        """Decompose user request into a detailed dependency plan using LLM."""
        prompt = f"""
        You are the AI Planner for DigiPay. Decompose the user request into a series of tool execution steps.
        User message: "{message}"
        Intent: {intent}
        Context merchantId (csc_id): "{csc_id}"
        
        Supported tools:
        - getWalletBalance (args: merchantId)
        - getLimits (args: merchantId)
        - getMerchantProfile (args: merchantId)
        - getMerchantStatus (args: merchantId)
        - getLedgerStatement (args: merchantId)
        - getTransaction (args: txnId)
        - reverseTransaction (args: txnId)
        - getPassbook (args: merchantId)
        - sendAlert (args: merchantId, title, body)
        - balanceEnquiry (args: merchantId)
        - cashWithdrawalStatus (args: txnId)
        - raiseTicket (args: merchantId, category, details)
        - closeTicket (args: ticketId)
        
        Rules:
        1. If user asks for balance, add getWalletBalance step.
        2. If user wants profile, add getMerchantProfile step.
        3. If reversing a transaction, add getTransaction first, and then reverseTransaction (which requires getTransaction step output).
        4. If a step is sensitive like reverseTransaction or sendAlert, set "requires_confirmation": true.
        5. Set "parallel": true for steps with no dependencies.
        
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
