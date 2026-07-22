import logging
from typing import Dict, Any, List
from prompts.manager import PROMPT_VERSIONS

logger = logging.getLogger("ai_platform.admin.prompt_service")

class PromptAdminService:
    @staticmethod
    def get_all_prompts() -> Dict[str, Any]:
        """Returns all registered system prompt templates and versions."""
        return {
            "availablePrompts": PROMPT_VERSIONS,
            "activeVersions": {
                "system_core": "v1"
            }
        }

    @staticmethod
    def update_prompt_template(key: str, version: str, template: str) -> Dict[str, Any]:
        """Dynamically update system prompt template without code redeployments."""
        if key not in PROMPT_VERSIONS:
            PROMPT_VERSIONS[key] = {}
            
        PROMPT_VERSIONS[key][version] = template
        logger.info(f"Admin updated prompt '{key}' version '{version}'")
        return {
            "key": key,
            "version": version,
            "template": template,
            "status": "UPDATED"
        }

prompt_admin_service = PromptAdminService()
