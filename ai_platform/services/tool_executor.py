import json
import logging
import time
from typing import Any, Dict, List, Optional

from core.exceptions import (
    AuthenticationException,
    TenantIsolationException,
    ToolExecutionException,
)
from messaging.formatter import message_formatter
from services.cache_service import cache_service
from services.permission_service import permission_service
from services.tool_runner import tool_runner_service
from tools.registry import get_tool

logger = logging.getLogger("ai_platform.services.tool_executor")

# Argument names that identify the record owner and are therefore subject to the
# tenant boundary check. cscId is the DigiPay gateway's spelling; merchantId is
# the pre-existing DigiPay tools' spelling.
OWNER_ARG_KEYS = ("merchantId", "merchant_id", "cscId", "csc_id")

# Roles legitimately allowed to read another user's records — the admin reports
# and support lookups exist precisely to do that. Their access is still gated by
# the per-tool RBAC list in the registry.
CROSS_TENANT_ROLES = ("ROLE_ADMIN", "ROLE_SUPPORT")

# Read-only fallback list for tools that predate the registry's read_only flag.
# The flag is authoritative; this only covers a name that is not registered.
LEGACY_READ_ONLY_TOOLS = (
    "getWalletBalance", "getLimits", "getMerchantProfile",
    "getMerchantStatus", "getLedgerStatement", "getTransaction",
    "getPassbook", "balanceEnquiry", "cashWithdrawalStatus",
)


class ToolExecutorService:
    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        user_roles: List[str],
        jwt_token: Optional[str] = None,
        caller_merchant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lookup tool, check permissions, query Redis cache, execute and log outcomes."""
        logger.info(f"Executing tool {tool_name} with args {args} | caller={caller_merchant_id}")

        meta = get_tool(tool_name)
        roles = user_roles or []

        # 0. Tenant Isolation check
        self._enforce_tenant_boundary(tool_name, args, roles, caller_merchant_id)

        # 1. RBAC Permissions validation via permission_service
        permission_service.check_permission(tool_name, roles)

        # 2. Redis Caching check via cache_service. Cache eligibility comes from
        #    the tool's own read_only metadata, so newly registered read APIs are
        #    cached without editing a list here.
        cacheable = self._is_cacheable(tool_name, meta)
        ttl = getattr(meta, "ttl", 30) if meta else 30

        if cacheable:
            cached_val = cache_service.get_cached_result(tool_name, args)
            if cached_val is not None:
                return {
                    "result": self._decode_cached(cached_val),
                    "cacheHit": True,
                    "latency_ms": 0.0,
                    "message": message_formatter.render(tool_name, self._decode_cached(cached_val)),
                }

        # 3. Execution via tool_runner_service
        start_time = time.time()
        try:
            res = await tool_runner_service.run_tool(tool_name, args, jwt_token)
            latency_ms = (time.time() - start_time) * 1000

            # 4. Cache back if read only
            if cacheable:
                cache_service.set_cached_result(tool_name, args, self._encode_for_cache(res), ttl=ttl)

            return {
                "result": res,
                "cacheHit": False,
                "latency_ms": latency_ms,
                "message": message_formatter.render(tool_name, res),
            }
        except Exception as e:
            logger.error(f"Execution failed for tool {tool_name}: {e}", exc_info=True)
            if isinstance(e, AuthenticationException):
                raise
            raise ToolExecutionException(f"Failed to execute tool {tool_name}: {str(e)}") from e

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _enforce_tenant_boundary(
        tool_name: str,
        args: Dict[str, Any],
        roles: List[str],
        caller_merchant_id: Optional[str],
    ):
        """
        Refuse a lookup aimed at a CSC ID / merchant ID other than the caller's.

        Admin and support roles are exempt because their tools exist to inspect
        other users' records; the registry's per-tool role list still restricts
        which of those tools they can reach at all.
        """
        if not caller_merchant_id:
            return
        if any(role in CROSS_TENANT_ROLES for role in roles):
            return

        for key in OWNER_ARG_KEYS:
            requested = args.get(key)
            if requested and str(requested).strip() != str(caller_merchant_id).strip():
                logger.error(
                    f"Tenant Boundary Breach Detected! Caller cscId={caller_merchant_id} "
                    f"tried to query {key}={requested} via {tool_name}"
                )
                raise TenantIsolationException(
                    f"Forbidden: Tenant Isolation Breach. You cannot access data for merchant '{requested}'."
                )

    @staticmethod
    def _is_cacheable(tool_name: str, meta) -> bool:
        if meta is not None:
            return bool(meta.read_only)
        return tool_name in LEGACY_READ_ONLY_TOOLS

    @staticmethod
    def _encode_for_cache(result: Any) -> str:
        """
        Store structured results as JSON so a cache hit returns the same shape as
        a live call. Falls back to str() for anything not JSON-serialisable.
        """
        try:
            return json.dumps({"__json__": result})
        except (TypeError, ValueError):
            return str(result)

    @staticmethod
    def _decode_cached(cached: Any) -> Any:
        if isinstance(cached, bytes):
            cached = cached.decode("utf-8", errors="replace")
        if isinstance(cached, str) and cached.startswith('{"__json__"'):
            try:
                return json.loads(cached)["__json__"]
            except (ValueError, KeyError):
                return cached
        return cached


tool_executor_service = ToolExecutorService()
