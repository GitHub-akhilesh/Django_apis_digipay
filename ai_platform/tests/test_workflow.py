import pytest
import json
from gateway.client import GatewayClient
from agent.orchestrator import AgentOrchestrator

@pytest.mark.anyio
async def test_ai_orchestrator_rag_and_formatting(monkeypatch):
    class MockResponse:
        def __init__(self, status_code, body=None):
            self.status_code = status_code
            self._body = body or {}
            self.text = json.dumps(self._body)
        def json(self):
            return self._body
            
    async def mock_request(method, endpoint_path, **kwargs):
        return MockResponse(200, {
            "success": True,
            "message": "Success",
            "data": {"balance": 4560.50, "currency": "INR"}
        })
        
    monkeypatch.setattr(GatewayClient, "request", mock_request)
    
    # 1. Test Wallet Balance Orchestration
    res = await AgentOrchestrator.chat(
        session_id="session_test_orchestrate",
        message="What is my active wallet balance?",
        csc_id="500100100014",
        history=[]
    )
    assert res["intent"] == "Wallet"
    assert "balance" in res["response"]
    
    # 2. Test FAQ/RAG Orchestration
    res_faq = await AgentOrchestrator.chat(
        session_id="session_test_faq",
        message="biometric face rd setup SOP documentation",
        csc_id="500100100014",
        history=[]
    )
    assert res_faq["intent"] == "FAQ"
    assert "Aadhaar Face RD" in res_faq["response"]
