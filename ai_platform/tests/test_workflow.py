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
        # Balance now resolves through the DigiPay gateway's ledger endpoint,
        # which answers with a CommonResponseBO envelope rather than the
        # {success, data} shape used by the pre-existing microservice clients.
        if endpoint_path.startswith("/v2/") or endpoint_path.startswith("/api/v2"):
            return MockResponse(200, {
                "status": "OK",
                "msg": "SUCCESS",
                "errors": [],
                "resData": {
                    "cscId": "500100100014",
                    "balance": 4560.50,
                    "blockedAmount": 120.0,
                },
            })
        return MockResponse(200, {
            "success": True,
            "message": "Success",
            "data": {"balance": 4560.50, "currency": "INR"}
        })

    monkeypatch.setattr(GatewayClient, "request", mock_request)

    # 1. Test Balance Orchestration.
    #
    # Routes to getLedgerBalanceV2 (GET /v2/ledger/balance), not the pre-existing
    # getWalletBalance: the latter calls /wallet/balance, which the DigiPay Spring
    # gateway does not serve, so it 401s and the user gets an escalation message
    # rather than a figure.
    res = await AgentOrchestrator.chat(
        session_id="session_test_orchestrate",
        message="What is my active wallet balance?",
        csc_id="500100100014",
        history=[]
    )
    assert res["intent"] == "LEDGER_BALANCE"
    assert res["escalate"] is False, f"balance lookup escalated: {res['response']}"
    assert "balance" in res["response"].lower()
    assert "4,560.50" in res["response"] or "4560.5" in res["response"]
    
    # 2. Test FAQ/RAG Orchestration
    res_faq = await AgentOrchestrator.chat(
        session_id="session_test_faq",
        message="biometric face rd setup SOP documentation",
        csc_id="500100100014",
        history=[]
    )
    assert res_faq["intent"] == "FAQ"
    assert "Aadhaar Face RD" in res_faq["response"]
