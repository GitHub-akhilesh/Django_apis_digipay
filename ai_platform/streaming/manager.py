import asyncio
import logging
from typing import AsyncGenerator
from streaming.events import StreamEvent, EventType
from streaming.token_stream import token_streamer
from agent.orchestrator import AgentOrchestrator

logger = logging.getLogger("ai_platform.streaming.manager")

class StreamManager:
    @staticmethod
    async def generate_chat_stream(
        session_id: str,
        message: str,
        csc_id: str,
        history: list,
        user_roles: list = None,
        jwt_token: str = None
    ) -> AsyncGenerator[str, None]:
        """Orchestrates structured events and streams tokens over Server-Sent Events (SSE)."""
        logger.info(f"Starting SSE chat stream for session {session_id}")
        
        # 1. Planner Started
        yield StreamEvent(EventType.PLANNER_STARTED, {"message": message, "cscId": csc_id}).to_sse()
        await asyncio.sleep(0.05)
        
        # 2. Invoke Orchestrator
        result = await AgentOrchestrator.chat(
            session_id=session_id,
            message=message,
            csc_id=csc_id,
            history=history,
            user_roles=user_roles,
            jwt_token=jwt_token
        )
        
        yield StreamEvent(EventType.PLANNER_COMPLETED, {
            "intent": result["intent"],
            "explainability": result.get("explainability", {})
        }).to_sse()
        await asyncio.sleep(0.05)

        # 3. Yield Tool Progress Events
        selected_tools = result.get("explainability", {}).get("selectedTools", [])
        for tool_name in selected_tools:
            yield StreamEvent(EventType.TOOL_STARTED, {"tool": tool_name}).to_sse()
            await asyncio.sleep(0.02)
            yield StreamEvent(EventType.TOOL_COMPLETED, {"tool": tool_name, "status": "SUCCESS"}).to_sse()
            await asyncio.sleep(0.02)

        # 4. Stream LLM Answer Tokens
        yield StreamEvent(EventType.LLM_STARTED, {"provider": "openai"}).to_sse()
        async for chunk in token_streamer.stream_tokens(result["response"]):
            yield chunk

        yield StreamEvent(EventType.LLM_COMPLETED, {}).to_sse()

        # 5. Conversation Completed
        yield StreamEvent(EventType.CONVERSATION_COMPLETED, {
            "sessionId": session_id,
            "escalate": result["escalate"]
        }).to_sse()

stream_manager = StreamManager()
