import logging
from typing import List
from tools.registry import validate_tool_permission

logger = logging.getLogger("ai_platform.services.permission_service")

class PermissionService:
    @staticmethod
    def check_permission(tool_name: str, user_roles: List[str]):
        """Enforces RBAC verification of tools access permissions."""
        validate_tool_permission(tool_name, user_roles)

permission_service = PermissionService()
