import logging
from typing import Dict, Any, List
from memory.session import session_metadata_memory
from services.chat_service import chat_service

logger = logging.getLogger("ai_platform.admin.conversation_service")

class ConversationAdminService:
    @staticmethod
    async def get_active_sessions() -> Dict[str, Any]:
        """Inspect all active chat sessions and lifecycle metadata."""
        sessions = []
        for session_id, meta_json in getattr(session_metadata_memory, "local_metadata", {}).items() if hasattr(session_metadata_memory, "local_metadata") else []:
            history = await chat_service.get_session_history(session_id)
            meta = session_metadata_memory.get_metadata(session_id)
            sessions.append({
                "sessionId": session_id,
                "messagesCount": len(history),
                "importance": meta.get("importance", 4.0),
                "lastIntent": meta.get("lastIntent", "N/A"),
                "lastTool": meta.get("lastTool", "N/A"),
                "merchantId": meta.get("merchantId", "N/A"),
                "userId": meta.get("userId", "N/A"),
                "conversationTokens": meta.get("conversationTokens", 0),
                "summary": meta.get("summary", "")
            })
        return {"totalSessions": len(sessions), "sessions": sessions}

    @staticmethod
    async def get_session_transcript(session_id: str) -> Dict[str, Any]:
        """Fetch full conversation message transcript for a session."""
        history = await chat_service.get_session_history(session_id)
        metadata = session_metadata_memory.get_metadata(session_id)
        return {
            "sessionId": session_id,
            "metadata": metadata,
            "transcript": history
        }

conversation_admin_service = ConversationAdminService()
