import logging
from llm.provider import BaseLLMProvider

logger = logging.getLogger("ai_platform.llm.gemini")

class GeminiProvider(BaseLLMProvider):
    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        logger.info("Gemini generate request")
        return self._simulate_response(prompt, system_instruction)
