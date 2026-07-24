import asyncio
import sys
import pytest

from app.database import AsyncSessionLocal
from app.routers.v1.agent import chat_with_agent, AgentChatRequest

class DummyRequest:
    state = type("State", (), {"user": None})()

@pytest.mark.asyncio
async def test_live_chat_endpoint():
    async with AsyncSessionLocal() as db:
        req = AgentChatRequest(
            sessionId="sess_live_123",
            cscId="500100100014",
            message="Check my wallet balance"
        )
        dummy_http_req = DummyRequest()
        res = await chat_with_agent(req, dummy_http_req, db)
        assert res.status == "OK"
