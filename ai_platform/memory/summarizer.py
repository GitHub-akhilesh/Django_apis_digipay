import logging
from typing import List, Dict
from llm.orchestrator import llm_orchestrator

logger = logging.getLogger("ai_platform.memory.summarizer")

class ConversationSummarizer:
    @staticmethod
    async def summarize_history(history: List[Dict[str, str]]) -> str:
        """Call LLM to summarize conversation history to compress token usage."""
        if not history:
            return ""
            
        prompt = f"""
        Provide a brief summary of this conversation between a support agent and merchant.
        History log:
        {history}
        
        Output only the summary string.
        """
        summary = await llm_orchestrator.generate(prompt, system_instruction="Conversation Summarizer")
        return summary.strip()
