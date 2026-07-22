import logging
from llm.provider import BaseLLMProvider
from llm.openai import OpenAIProvider
from llm.gemini import GeminiProvider
from llm.ollama import OllamaProvider

logger = logging.getLogger("ai_platform.llm.factory")

class LLMProviderFactory:
    @staticmethod
    def get_provider(provider_name: str = "openai") -> BaseLLMProvider:
        logger.info(f"Instantiating LLM Provider: {provider_name}")
        name = provider_name.lower()
        if name == "openai":
            return OpenAIProvider()
        elif name == "gemini":
            return GeminiProvider()
        elif name == "ollama":
            return OllamaProvider()
        else:
            logger.warning(f"Unknown LLM provider: {name}. Defaulting to OpenAI.")
            return OpenAIProvider()
