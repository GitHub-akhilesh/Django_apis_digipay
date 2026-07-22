import time
import logging
from typing import List, Dict, Any, Optional
from services.permission_service import permission_service
from services.cache_service import cache_service
from services.tool_runner import tool_runner_service
from core.exceptions import ToolExecutionException, AuthenticationException

logger = logging.getLogger("ai_platform.services.tool_executor")

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
        
        # 0. Tenant Isolation check
        if caller_merchant_id:
            m_id = args.get("merchantId") or args.get("merchant_id")
            if m_id and str(m_id).strip() != str(caller_merchant_id).strip():
                logger.error(f"Tenant Boundary Breach Detected! Caller cscId={caller_merchant_id} tried to query merchantId={m_id}")
                raise AuthenticationException(
                    f"Forbidden: Tenant Isolation Breach. You cannot access data for merchant '{m_id}'."
                )

        # 1. RBAC Permissions validation via permission_service
        permission_service.check_permission(tool_name, user_roles)
        
        # 2. Redis Caching check via cache_service
        read_only_tools = [
            "getWalletBalance", "getLimits", "getMerchantProfile",
            "getMerchantStatus", "getLedgerStatement", "getTransaction",
            "getPassbook", "balanceEnquiry", "cashWithdrawalStatus"
        ]
        
        if tool_name in read_only_tools:
            cached_val = cache_service.get_cached_result(tool_name, args)
            if cached_val is not None:
                return {
                    "result": cached_val,
                    "cacheHit": True,
                    "latency_ms": 0.0
                }

        # 3. Execution via tool_runner_service
        start_time = time.time()
        try:
            res = await tool_runner_service.run_tool(tool_name, args, jwt_token)
            latency_ms = (time.time() - start_time) * 1000
            
            # 4. Cache back if read only
            if tool_name in read_only_tools:
                cache_service.set_cached_result(tool_name, args, str(res))
                    
            return {
                "result": res,
                "cacheHit": False,
                "latency_ms": latency_ms
            }
        except Exception as e:
            logger.error(f"Execution failed for tool {tool_name}: {e}", exc_info=True)
            if isinstance(e, AuthenticationException):
                raise
            raise ToolExecutionException(f"Failed to execute tool {tool_name}: {str(e)}") from e

tool_executor_service = ToolExecutorService()
