import pytest
import json
from gateway.client import GatewayClient
from planner.service import PlannerService
from agent.orchestrator import AgentOrchestrator
from memory.session import session_metadata_memory

@pytest.mark.anyio
async def test_planner_multi_step_dag_and_confirmation(monkeypatch):
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

    # 1. Clear session metadata memory first
    session_metadata_memory.save_metadata("session_dag_test", {})

    # 2. Trigger transaction reversal (requires confirmation)
    res = await AgentOrchestrator.chat(
        session_id="session_dag_test",
        message="Please process reversal for transaction 123",
        csc_id="500100100014",
        history=[]
    )
    # The orchestrator should halt, output confirmation prompt, and wait
    assert "confirm" in res["response"].lower()
    
    # 3. Verify session state is saved as awaiting confirmation
    meta = session_metadata_memory.get_metadata("session_dag_test")
    assert meta["awaiting_confirmation"] is True
    assert len(meta["plan_steps"]) > 0
    
    # 4. Send "CONFIRM" to trigger execution
    res_confirm = await AgentOrchestrator.chat(
        session_id="session_dag_test",
        message="CONFIRM",
        csc_id="500100100014",
        history=[]
    )
    # Reversal should be executed successfully now
    assert "confirm" not in res_confirm["response"].lower()
