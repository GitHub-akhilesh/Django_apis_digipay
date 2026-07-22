import logging
from typing import Dict, Any, List
from llm.factory import LLMProviderFactory

logger = logging.getLogger("ai_platform.services.planner_service")

class PlannerService:
    @staticmethod
    async def create_plan(message: str, intent: str, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Decide if tools are required or if FAQ/general answers are needed."""
        need_tool = len(tool_calls) > 0
        return {
            "need_tool": need_tool,
            "tool_calls": tool_calls
        }
