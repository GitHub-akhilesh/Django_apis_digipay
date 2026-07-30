import logging
from typing import List, Optional

from core.config import settings
from core.exceptions import PermissionDeniedException
from tools.decorator import (
    HEALTH_UNREACHABLE,
    LEGACY_MICROSERVICE_TOOLS,
    REGISTERED_TOOLS,
    ToolMetadata,
)
from tools.discovery import discover_tools

logger = logging.getLogger("ai_platform.tools.registry")

# The UNREACHABLE decision itself lives in tools.decorator, applied at
# registration so re-running discovery cannot reset it. Re-exported here because
# this module is the registry's public surface.
# Gateway equivalents, surfaced in logs and diagnostics so the replacement for a
# withheld tool is discoverable rather than guesswork.
LEGACY_TOOL_REPLACEMENTS = {
    "getWalletBalance": "getLedgerBalanceV2",
    "getLimits": None,
    "getMerchantProfile": "adminGetUserDetails",
    "getMerchantStatus": "adminGetUserDetails",
    "getLedgerStatement": "getLedgerPassbookV2",
    "getPassbook": "getLedgerPassbookV2",
    "getTransaction": "getTxnLogs",
    "balanceEnquiry": "getAepsBalanceEnquiryDetails",
    "cashWithdrawalStatus": "getAepsLogDetails",
    "reverseTransaction": None,
    "sendAlert": None,
}

# Auto-discover tools dynamically
TOOL_REGISTRY = discover_tools()


def _report_unreachable_tools():
    """Log which tools are withheld, so the state is visible at startup."""
    withheld = sorted(
        name for name, meta in TOOL_REGISTRY.items()
        if meta.health == HEALTH_UNREACHABLE
    )
    if withheld:
        logger.warning(
            "%s pre-existing tools reference SERVICE_ENDPOINTS paths that the configured "
            "gateway (%s) does not serve; marked %s and withheld from the tool catalogue. "
            "Set LEGACY_MICROSERVICE_ENDPOINTS_ENABLED=true to re-enable them. Tools: %s",
            len(withheld), settings.API_GATEWAY_URL, HEALTH_UNREACHABLE, ", ".join(withheld),
        )


_report_unreachable_tools()


def validate_tool_permission(tool_name: str, user_roles: List[str]):
    """Check if caller's user_roles satisfy tool's metadata roles list."""
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return

    allowed_roles = getattr(tool, "roles", ["ROLE_USER", "ROLE_MERCHANT", "ROLE_SUPPORT", "ROLE_ADMIN"])
    if not any(r in allowed_roles for r in user_roles):
        raise PermissionDeniedException(
            f"Forbidden: Your roles {user_roles} lack permission to execute tool '{tool_name}'."
        )


def get_tool(tool_name: str) -> Optional[ToolMetadata]:
    return TOOL_REGISTRY.get(tool_name)


def is_read_only(tool_name: str) -> bool:
    """
    Whether a tool's backing API only reads.

    Unknown tools are treated as state-changing so an unregistered name is never
    cached or auto-executed on the assumption that it is harmless.
    """
    tool = TOOL_REGISTRY.get(tool_name)
    return bool(tool and tool.read_only)


def requires_confirmation(tool_name: str) -> bool:
    tool = TOOL_REGISTRY.get(tool_name)
    return bool(tool and (tool.requires_confirmation or not tool.read_only))
