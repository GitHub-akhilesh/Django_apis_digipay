import re
import logging
from typing import Dict, Any, Optional
from tools.registry import TOOL_REGISTRY
from core.exceptions import ToolExecutionException

logger = logging.getLogger("ai_platform.services.tool_runner")

class ToolRunnerService:
    @staticmethod
    def _convert_args(args: Dict[str, Any]) -> Dict[str, Any]:
        """Convert camelCase keys to snake_case parameters dynamically."""
        new_args = {}
        for k, v in args.items():
            if k == "merchantId":
                new_args["merchant_id"] = v
            elif k == "txnId":
                new_args["txn_id"] = v
            elif k == "ticketId":
                new_args["ticket_id"] = v
            elif k == "fromDate":
                new_args["from_date"] = v
            elif k == "toDate":
                new_args["to_date"] = v
            else:
                snake_k = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
                new_args[snake_k] = v
        return new_args

    async def run_tool(self, tool_name: str, args: Dict[str, Any], jwt_token: Optional[str] = None) -> Any:
        """Looks up the tool and executes the wrapped function callable."""
        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            raise ToolExecutionException(f"Tool {tool_name} not registered.")
            
        converted = self._convert_args(args)
        kwargs = {**converted}
        if jwt_token:
            kwargs["jwt_token"] = jwt_token
            
        return await tool.func(**kwargs)

tool_runner_service = ToolRunnerService()
