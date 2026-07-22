import logging
from llm.provider import BaseLLMProvider

logger = logging.getLogger("ai_platform.llm.ollama")

class OllamaProvider(BaseLLMProvider):
    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        logger.info("Ollama local generation request")
        return self._simulate_response(prompt, system_instruction)
