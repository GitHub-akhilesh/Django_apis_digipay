import pytest
import json
from gateway.client import GatewayClient
from services.tool_executor import tool_executor_service
from core.exceptions import AuthenticationException

@pytest.mark.anyio
async def test_tool_executor_rbac_and_caching(monkeypatch):
    class MockResponse:
        def __init__(self, status_code, body=None):
            self.status_code = status_code
            self._body = body or {}
            self.text = json.dumps(self._body)
        def json(self):
            return self._body
            
    async def mock_request(method, endpoint_path, **kwargs):
        if "transaction" in endpoint_path:
            return MockResponse(200, {
                "success": True,
                "message": "Success",
                "data": {
                    "txnId": "123",
                    "amount": 1000.0,
                    "status": "REVERSED",
                    "merchantId": "500100100014",
                    "timestamp": "2026-07-20T18:00:00Z"
                }
            })
        return MockResponse(200, {
            "success": True,
            "message": "Success",
            "data": {"balance": 4560.50, "currency": "INR"}
        })
        
    monkeypatch.setattr(GatewayClient, "request", mock_request)
    
    # 1. Reversal is restricted to ROLE_SUPPORT or ROLE_ADMIN. Ensure ROLE_MERCHANT is rejected.
    with pytest.raises(AuthenticationException) as exc_info:
        await tool_executor_service.execute_tool(
            tool_name="reverseTransaction",
            args={"txnId": "123"},
            user_roles=["ROLE_MERCHANT"]
        )
    assert "Forbidden" in str(exc_info.value)

    # 2. Reversal is accepted for ROLE_SUPPORT.
    res_reversal = await tool_executor_service.execute_tool(
        tool_name="reverseTransaction",
        args={"txnId": "123"},
        user_roles=["ROLE_SUPPORT"]
    )
    assert "processed" in res_reversal["result"]
