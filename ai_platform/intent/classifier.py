import json
import logging
from typing import Dict, Any
from llm.orchestrator import llm_orchestrator
from intent.registry import INTENT_REGISTRY

logger = logging.getLogger("ai_platform.intent.classifier")

class IntentClassifier:
    @staticmethod
    async def classify(message: str, csc_id: str) -> Dict[str, Any]:
        """Use LLM prompts to classify user message intent."""
        prompt = f"""
        Given the user message, classify the query into exactly one of these intents:
        {INTENT_REGISTRY}
        
        User Query: "{message}"
        Caller context: merchantId (csc_id) = "{csc_id}"
        
        You must output exactly a JSON object in this format:
        {{
          "intent": "<intent>",
          "confidence": <float between 0.0 and 1.0>,
          "tool_calls": [
            {{"name": "<tool_name>", "args": {{...}}}}
          ]
        }}
        
        Valid tool names:
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
        
        Output only valid JSON. Do not include markdown wraps.
        """
        resp = await llm_orchestrator.generate(prompt, system_instruction="Intent Classifier Node")
        
        try:
            clean_json = resp.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            
            data = json.loads(clean_json)
            return {
                "intent": data.get("intent", "GENERAL"),
                "confidence": data.get("confidence", 1.0),
                "tool_calls": data.get("tool_calls", [])
            }
        except Exception as e:
            logger.error(f"Failed to parse classification JSON: {resp} - Error: {e}")
            return {
                "intent": "GENERAL",
                "confidence": 0.5,
                "tool_calls": []
            }
