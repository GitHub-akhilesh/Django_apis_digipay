import asyncio
import logging
from typing import Dict, Any, List, Optional
from core.exceptions import LLMException
from llm.factory import LLMProviderFactory
from monitoring.mdc import TraceContext

logger = logging.getLogger("ai_platform.llm.orchestrator")

MODEL_PRICING = {
    "openai": {"model": "gpt-4o", "input_rate": 0.005, "output_rate": 0.015},
    "gemini": {"model": "gemini-1.5-pro", "input_rate": 0.007, "output_rate": 0.021},
    "ollama": {"model": "llama3", "input_rate": 0.0, "output_rate": 0.0}
}

class EnterpriseLLMOrchestrator:
    def __init__(self):
        # Configure the priority sequence for failover
        self.priority_list = ["openai", "gemini", "ollama"]
        self.timeout_seconds = 5.0
        self.pricing = MODEL_PRICING

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return int(len(text.split()) * 1.3) + 1

    def _calculate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        pricing = MODEL_PRICING.get(provider, {"input_rate": 0.0, "output_rate": 0.0})
        cost = (input_tokens / 1000.0) * pricing["input_rate"] + (output_tokens / 1000.0) * pricing["output_rate"]
        return round(cost, 6)

    async def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        model_version: str = "v1"
    ) -> str:
        """Executes LLM generation with automatic failover, exponential retries, and token accounting."""
        last_error = None
        
        for provider_name in self.priority_list:
            provider = LLMProviderFactory.get_provider(provider_name)
            
            retries = 3
            backoff = 0.2
            for attempt in range(1, retries + 1):
                try:
                    logger.info(f"Attempting LLM generate via {provider_name} (Attempt {attempt}/{retries})")
                    
                    # Dynamic timeout enforcement
                    result = await asyncio.wait_for(
                        provider.generate(prompt, system_instruction),
                        timeout=self.timeout_seconds
                    )
                    
                    in_tokens = self._estimate_tokens(prompt) + self._estimate_tokens(system_instruction)
                    out_tokens = self._estimate_tokens(result)
                    cost = self._calculate_cost(provider_name, in_tokens, out_tokens)
                    
                    logger.info(f"LLM request succeeded via {provider_name}. Cost: ${cost:.6f}, Tokens: in={in_tokens}/out={out_tokens}")
                    
                    # Update MDC Context variables dynamically for operational dashboards
                    TraceContext.process_txn(
                        model=MODEL_PRICING[provider_name]["model"],
                        prompt_tokens=in_tokens,
                        completion_tokens=out_tokens,
                        cost=cost,
                        provider=provider_name,
                        retry_count=attempt - 1
                    )
                    
                    return result
                except Exception as e:
                    logger.warning(f"Attempt {attempt} failed on {provider_name}: {e}")
                    last_error = e
                    await asyncio.sleep(backoff)
                    backoff *= 2
            
            logger.error(f"Provider {provider_name} exhausted all retries. Falling back to next provider.")
            
        raise LLMException(f"All LLM providers failed. Last error: {last_error}")

llm_orchestrator = EnterpriseLLMOrchestrator()
