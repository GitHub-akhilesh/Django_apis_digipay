import logging
from typing import Dict, Any, List
from tools.registry import TOOL_REGISTRY

logger = logging.getLogger("ai_platform.admin.tool_service")

class ToolAdminService:
    @staticmethod
    def get_registered_tools() -> Dict[str, Any]:
        """Returns details for all registered tools in the platform."""
        tool_list = []
        for name, meta in TOOL_REGISTRY.items():
            tool_list.append({
                "name": meta.name,
                "description": meta.description,
                "roles": meta.roles,
                "cacheable": meta.cacheable,
                "ttl": meta.ttl,
                "timeout": meta.timeout,
                "retries": meta.retries,
                "version": getattr(meta, "version", "1.0"),
                "deprecated": getattr(meta, "deprecated", False),
                "owner": getattr(meta, "owner", "DigiPay Platform Team"),
                "health": getattr(meta, "health", "HEALTHY")
            })
        return {"totalTools": len(tool_list), "tools": tool_list}

    @staticmethod
    def update_tool_governance(name: str, roles: List[str] = None, health: str = None, deprecated: bool = None) -> Dict[str, Any]:
        """Update tool roles, health status, or deprecation flag dynamically."""
        meta = TOOL_REGISTRY.get(name)
        if not meta:
            return {"error": f"Tool '{name}' not found."}

        if roles is not None:
            meta.roles = roles
        if health is not None:
            meta.health = health
        if deprecated is not None:
            meta.deprecated = deprecated

        logger.info(f"Admin updated tool governance for '{name}'")
        return {
            "name": name,
            "roles": meta.roles,
            "health": meta.health,
            "deprecated": meta.deprecated,
            "status": "UPDATED"
        }

tool_admin_service = ToolAdminService()
