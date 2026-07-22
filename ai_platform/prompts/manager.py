import logging

logger = logging.getLogger("ai_platform.prompts.manager")

PROMPT_VERSIONS = {
    "system_core": {
        "v1": """
You are the DigiPay AI Assistant, a professional support virtual agent for the CSC VLEs and merchants.
Your tone should be helpful, brief, friendly, and precise.
Always adhere to compliance rules and avoid disclosing sensitive customer details (like full Aadhaar or Phone numbers) directly.
""",
        "v2": """
You are the advanced DigiPay virtual service agent. Answer concisely, format numeric/rupee parameters using ₹, and redact Aadhaar/Phone PII fields completely.
"""
    }
}

class PromptManager:
    @staticmethod
    def get_prompt(prompt_key: str, version: str = "v1") -> str:
        versions = PROMPT_VERSIONS.get(prompt_key)
        if not versions:
            logger.warning(f"Prompt key '{prompt_key}' not found in versions registry.")
            return ""
        val = versions.get(version)
        if not val:
            logger.warning(f"Prompt version '{version}' for key '{prompt_key}' not found. Defaulting to 'v1'.")
            return versions.get("v1", "")
        return val

prompt_manager = PromptManager()
