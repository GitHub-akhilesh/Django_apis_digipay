import json
import logging
from typing import List, Dict, Optional
import redis
from core.config import settings

logger = logging.getLogger("ai_platform.memory.redis_memory")

class SessionMemory:
    def __init__(self):
        self.redis_client = None
        self.use_redis = False
        try:
            redis_host = settings.REDIS_HOST
            if not redis_host or "${" in redis_host:
                redis_host = "127.0.0.1"
                
            self.redis_client = redis.Redis(
                host=redis_host,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                socket_timeout=1.5,
                decode_responses=True
            )
            self.redis_client.ping()
            self.use_redis = True
            logger.info("Connected to Redis successfully for AI session memory.")
        except Exception as e:
            logger.warning(f"Redis memory store failed to initialize: {e}. Falling back to local dictionary.")
            self.use_redis = False

        # In-memory dictionary fallback
        self.local_store: Dict[str, List[Dict[str, str]]] = {}
        self.local_metadata: Dict[str, str] = {}
        self.local_summary: Dict[str, str] = {}

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieve the recent chat log for a session."""
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get(f"ai_memory:session:{session_id}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Redis memory retrieval failed for {session_id}: {e}")
        return self.local_store.get(session_id, [])

    def save_history(self, session_id: str, messages: List[Dict[str, str]]):
        """Saves session chat history, trimming to the last 10 exchanges."""
        trimmed = messages[-10:]
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.setex(
                    f"ai_memory:session:{session_id}",
                    86400,  # Expires after 24 hours
                    json.dumps(trimmed)
                )
                return
            except Exception as e:
                logger.error(f"Redis memory save failed for {session_id}: {e}")
        self.local_store[session_id] = trimmed

    def clear_history(self, session_id: str):
        """Clears memory for a given session."""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(f"ai_memory:session:{session_id}")
            except Exception as e:
                logger.error(f"Redis memory delete failed for {session_id}: {e}")
        if session_id in self.local_store:
            del self.local_store[session_id]

# Singleton instance
session_memory = SessionMemory()
