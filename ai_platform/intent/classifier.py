import json
import logging
from typing import Any, Dict, List, Optional

from intent.registry import INTENT_REGISTRY
from llm.orchestrator import llm_orchestrator
from tools.catalog import build_tool_catalog

logger = logging.getLogger("ai_platform.intent.classifier")


class IntentClassifier:
    @staticmethod
    async def classify(
        message: str,
        csc_id: str,
        user_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Classify a user message into an intent plus candidate tool calls.

        The tool list is generated from the live registry and filtered to the
        caller's roles, so newly integrated gateway APIs become classifiable the
        moment they are registered — and a merchant is never offered an admin
        report it would only be refused for.
        """
        tool_catalog = build_tool_catalog(roles=user_roles, include_examples=True)

        prompt = f"""
        Given the user message, classify the query into exactly one of these intents:
        {INTENT_REGISTRY}

        User Query: "{message}"
        Caller context: merchantId (csc_id) = "{csc_id}"
        Caller roles: {user_roles or ["ROLE_MERCHANT"]}

        You must output exactly a JSON object in this format:
        {{
          "intent": "<intent>",
          "confidence": <float between 0.0 and 1.0>,
          "tool_calls": [
            {{"name": "<tool_name>", "args": {{...}}}}
          ]
        }}

        Available tools, grouped by domain:
        {tool_catalog}

        Rules:
        1. Only use tool names that appear in the list above.
        2. Populate cscId or merchantId arguments from the caller context, never from guesses.
        3. Dates use dd-MM-yyyy.
        4. If the user asks a policy, process or how-to question rather than for their
           own data, classify as FAQ and return no tool calls.
        5. If the user asks you to move money, reverse or refund a payment, block a user,
           register a device, create or delete a record, or authenticate a customer,
           classify as UNSUPPORTED_ACTION and return no tool calls.

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
