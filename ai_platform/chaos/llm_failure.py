import logging
from llm.orchestrator import llm_orchestrator

logger = logging.getLogger("ai_platform.chaos.llm_failure")

class LLMFailureSimulator:
    def __init__(self):
        self._original_priority = list(llm_orchestrator.priority_list)

    def inject_primary_failure(self):
        """Simulate OpenAI connection errors by modifying priority chain."""
        logger.warning("Injecting LLM Provider Failure Chaos (OpenAI disabled)...")
        # Change priority sequence to bypass openai or force it to fail
        llm_orchestrator.priority_list = ["gemini", "ollama"]

    def recover(self):
        """Restore provider lists."""
        logger.info("Recovering LLM Providers priority list...")
        llm_orchestrator.priority_list = self._original_priority

llm_failure_simulator = LLMFailureSimulator()
