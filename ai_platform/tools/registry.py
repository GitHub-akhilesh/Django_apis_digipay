import logging
from typing import List
from tools.decorator import REGISTERED_TOOLS, ToolMetadata
from tools.discovery import discover_tools
from core.exceptions import AuthenticationException

logger = logging.getLogger("ai_platform.tools.registry")

# Auto-discover tools dynamically
TOOL_REGISTRY = discover_tools()

def validate_tool_permission(tool_name: str, user_roles: List[str]):
    """Check if caller's user_roles satisfy tool's metadata roles list."""
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return
        
    allowed_roles = getattr(tool, "roles", ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"])
    if not any(r in allowed_roles for r in user_roles):
        raise AuthenticationException(
            f"Forbidden: Your roles {user_roles} lack permission to execute tool '{tool_name}'."
        )
