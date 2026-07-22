import logging
from llm.provider import BaseLLMProvider
from core.config import settings

logger = logging.getLogger("ai_platform.llm.openai")

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.active = self.api_key is not None and self.api_key.startswith("sk-")

    async def generate(self, prompt: str, system_instruction: str = "") -> str:
        logger.info(f"OpenAI generate request (active={self.active})")
        if not self.active:
            return self._simulate_response(prompt, system_instruction)
        
        # In actual prod, we import openai client and run chat completions:
        # response = await openai.ChatCompletion.acreate(...)
        return "Actual completions result"
