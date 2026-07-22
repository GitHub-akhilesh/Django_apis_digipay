import pytest
import jwt
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from main import app
from core.config import settings
from tools.registry import TOOL_REGISTRY
from streaming.events import StreamEvent, EventType
from streaming.token_stream import token_streamer
from agent.orchestrator import AgentOrchestrator

client = TestClient(app)

def generate_test_token(csc_id: str = "500100100014") -> str:
    payload = {
        "sub": "testuser",
        "cscId": csc_id,
        "roles": ["ROLE_USER", "ROLE_MERCHANT"],
        "exp": int(datetime.now(UTC).timestamp()) + 3600
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def test_tool_governance_metadata():
    tool_meta = TOOL_REGISTRY.get("getWalletBalance")
    assert tool_meta is not None
    assert hasattr(tool_meta, "version")
    assert hasattr(tool_meta, "deprecated")
    assert hasattr(tool_meta, "owner")
    assert hasattr(tool_meta, "health")
    assert tool_meta.version == "1.0"
    assert tool_meta.health == "HEALTHY"

def test_stream_event_sse_format():
    ev = StreamEvent(EventType.PLANNER_STARTED, {"intent": "WALLET"})
    sse_data = ev.to_sse()
    assert sse_data.startswith("data: {")
    assert EventType.PLANNER_STARTED in sse_data

@pytest.mark.anyio
async def test_token_streamer_generator():
    chunks = []
    async for chunk in token_streamer.stream_tokens("Hello DigiPay World", delay_ms=1):
        chunks.append(chunk)
    assert len(chunks) == 3
    assert "Hello" in chunks[0]

@pytest.mark.anyio
async def test_planner_explainability_output():
    res = await AgentOrchestrator.chat(
        session_id="session_explain_test",
        message="Check wallet balance",
        csc_id="500100100014",
        history=[]
    )
    assert "explainability" in res
    exp = res["explainability"]
    assert exp["intent"] == "Wallet"
    assert "selectedTools" in exp
    assert "executionTimeMs" in exp

def test_sse_streaming_endpoint():
    token = generate_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/chat/stream",
        headers=headers,
        json={"sessionId": "stream_123", "message": "What is my balance?"}
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "PlannerStarted" in response.text or "TokenGenerated" in response.text
