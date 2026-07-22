import pytest
import json
import logging
import asyncio
from fastapi.testclient import TestClient
from main import app
from core.config import settings
from core.error_codes import ErrorCode
from core.exceptions import (
    AuthenticationException,
    ValidationException,
    ToolExecutionException,
    LLMException,
    GatewayException
)
from core.logger import JSONFormatter
from core.constants import HEADER_B3_TRACE_ID, HEADER_B3_SPAN_ID, HEADER_CORRELATION_ID
from monitoring.mdc import TraceContext, txn_id_var, merchant_id_var, service_name_var, tool_var
from gateway.client import GatewayClient
from gateway.base_client import BaseGatewayClient, CircuitState

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}

def test_ready_endpoint():
    response = client.get("/ready")
    assert response.status_code in [200, 503]
    body = response.json()
    assert "redis" in body
    assert "gateway" in body
    assert "version" in body

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200

def test_exceptions_request_id_and_hierarchy():
    e1 = AuthenticationException("Token failed validation check")
    assert e1.status_code == 401
    assert e1.request_id != ""

    e2 = ValidationException("Missing cscId input parameter")
    assert e2.status_code == 400

    e3 = ToolExecutionException("Tool write failed")
    assert e3.status_code == 502

    e5 = GatewayException("Ledger endpoint unavailable")
    assert e5.status_code == 504

def test_process_txn_mdc_and_logger():
    TraceContext.process_txn(
        txn_id="TXN-AI-8888",
        merchant_id="CSC-AI-8888",
        service="AI_PLATFORM",
        channel="AEPS",
        tool="wallet_balance_tool",
        model="gpt-5.5",
        prompt_tokens=350,
        completion_tokens=150,
        cost=0.005,
        provider="openai",
        cache_hit=True,
        retry_count=1
    )
    
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="ai_platform.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="AI request processed successfully",
        args=None,
        exc_info=None
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    
    assert parsed["txnId"] == "TXN-AI-8888"
    assert parsed["merchantId"] == "CSC-AI-8888"
    assert parsed["tool"] == "wallet_balance_tool"
    assert parsed["model"] == "gpt-5.5"
    assert parsed["promptTokens"] == 350
    assert parsed["completionTokens"] == 150
    assert parsed["cost"] == 0.005
    assert parsed["provider"] == "openai"
    assert parsed["cacheHit"] is True
    assert parsed["retryCount"] == 1

    TraceContext.clear()

def test_gateway_client_headers():
    downstream_headers = GatewayClient._prepare_headers(jwt_token="mock_token")
    assert HEADER_B3_TRACE_ID in downstream_headers
    assert HEADER_B3_SPAN_ID in downstream_headers
    assert HEADER_CORRELATION_ID in downstream_headers

@pytest.mark.anyio
async def test_gateway_sdk_clients(monkeypatch):
    from gateway.wallet_client import WalletClient
    
    class MockResponse:
        status_code = 200
        def __init__(self, body):
            self._body = body
            self.text = json.dumps(self._body)
        def json(self):
            return self._body

    async def mock_request(*args, **kwargs):
        return MockResponse({
            "success": True,
            "message": "Success",
            "data": {"balance": 4560.50, "currency": "INR"}
        })

    monkeypatch.setattr(GatewayClient, "request", mock_request)
    
    wallet_cli = WalletClient()
    res = await wallet_cli.get_balance("500100100014")
    assert res.balance == 4560.50

@pytest.mark.anyio
async def test_gateway_resilience_policies(monkeypatch):
    BaseGatewayClient._breakers.clear()
    
    class MockResponse:
        def __init__(self, status_code):
            self.status_code = status_code
            self._body = {"success": False, "message": "Service Timeout"}
            self.text = json.dumps(self._body)
        def json(self):
            return self._body

    call_count = 0
    async def mock_request_fail(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return MockResponse(504)

    monkeypatch.setattr(GatewayClient, "request", mock_request_fail)

    from gateway.aeps_client import AEPSClient
    aeps_cli = AEPSClient()
    for _ in range(5):
        try:
            await aeps_cli.balance_enquiry("M_AEPS")
        except GatewayException:
            pass

    with pytest.raises(GatewayException) as exc_info:
        await aeps_cli.balance_enquiry("M_AEPS")
    assert "Circuit Breaker is OPEN" in str(exc_info.value)
    assert call_count == 20
