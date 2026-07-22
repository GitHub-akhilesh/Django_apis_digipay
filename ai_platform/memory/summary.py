import logging
from typing import Optional
from memory.redis_memory import session_memory

logger = logging.getLogger("ai_platform.memory.summary")

class SummaryMemory:
    @staticmethod
    def get_summary(session_id: str) -> Optional[str]:
        """Fetch summary context from Redis store, falling back to local memory if offline."""
        if session_memory.use_redis and session_memory.redis_client:
            try:
                return session_memory.redis_client.get(f"ai_memory:summary:{session_id}")
            except Exception as e:
                logger.error(f"Failed to fetch summary: {e}")
        else:
            return session_memory.local_summary.get(session_id)
        return None

    @staticmethod
    def save_summary(session_id: str, summary: str):
        """Save summary context to Redis store, falling back to local memory if offline."""
        if session_memory.use_redis and session_memory.redis_client:
            try:
                session_memory.redis_client.setex(f"ai_memory:summary:{session_id}", 86400, summary)
            except Exception as e:
                logger.error(f"Failed to save summary: {e}")
        else:
            session_memory.local_summary[session_id] = summary

summary_memory = SummaryMemory()
