import logging
from llm.orchestrator import llm_orchestrator

logger = logging.getLogger("ai_platform.services.llm_service")

class LLMService:
    async def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        """Centralized LLM generation wrapper."""
        return await llm_orchestrator.generate(prompt, system_instruction)

llm_service = LLMService()
