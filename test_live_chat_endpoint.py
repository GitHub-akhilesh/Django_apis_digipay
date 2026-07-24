import asyncio
import sys

sys.stdout.reconfigure(encoding='utf-8')

from app.database import AsyncSessionLocal
from app.routers.v1.agent import chat_with_agent, AgentChatRequest

class DummyRequest:
    state = type("State", (), {"user": None})()

async def main():
    async with AsyncSessionLocal() as db:
        req = AgentChatRequest(
            sessionId="sess_live_123",
            cscId="500100100014",
            message="Check my wallet balance"
        )
        dummy_http_req = DummyRequest()
        try:
            res = await chat_with_agent(req, dummy_http_req, db)
            print("CHAT SUCCESS:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
