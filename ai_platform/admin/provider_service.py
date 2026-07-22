import logging
from typing import Dict, Any, List
from llm.orchestrator import llm_orchestrator

logger = logging.getLogger("ai_platform.admin.provider_service")

class ProviderAdminService:
    @staticmethod
    def get_provider_config() -> Dict[str, Any]:
        """Returns LLM provider configurations, fallback priorities, and timeouts."""
        priority = llm_orchestrator.priority_list
        primary = priority[0] if priority else "openai"
        fallbacks = priority[1:] if len(priority) > 1 else []
        return {
            "primaryProvider": primary,
            "fallbackProviders": fallbacks,
            "timeoutSeconds": llm_orchestrator.timeout_seconds,
            "pricing": llm_orchestrator.pricing
        }

    @staticmethod
    def update_provider_priorities(primary: str, fallbacks: List[str], timeout: int = 5) -> Dict[str, Any]:
        """Update provider fallback order and API call timeouts online."""
        llm_orchestrator.priority_list = [primary] + fallbacks
        llm_orchestrator.timeout_seconds = float(timeout)
        logger.info(f"Admin updated provider config: Primary={primary}, Fallbacks={fallbacks}, Timeout={timeout}s")
        return {
            "primaryProvider": primary,
            "fallbackProviders": fallbacks,
            "timeoutSeconds": timeout,
            "status": "UPDATED"
        }

provider_admin_service = ProviderAdminService()
