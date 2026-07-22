import json
import logging
from typing import Dict, Any
from memory.redis_memory import session_memory

logger = logging.getLogger("ai_platform.memory.session")

class SessionMetadataMemory:
    @staticmethod
    def get_metadata(session_id: str) -> Dict[str, Any]:
        """Fetch metadata dictionary mapping from Redis, falling back to local memory if offline."""
        if session_memory.use_redis and session_memory.redis_client:
            try:
                val = session_memory.redis_client.get(f"ai_memory:metadata:{session_id}")
                if val:
                    return json.loads(val)
            except Exception as e:
                logger.error(f"Failed to fetch session metadata: {e}")
        else:
            val = session_memory.local_metadata.get(session_id)
            if val:
                return json.loads(val)
        return {}

    @staticmethod
    def save_metadata(session_id: str, metadata: Dict[str, Any]):
        """Save metadata mapping to Redis, falling back to local memory if offline."""
        if session_memory.use_redis and session_memory.redis_client:
            try:
                session_memory.redis_client.setex(f"ai_memory:metadata:{session_id}", 86400, json.dumps(metadata))
            except Exception as e:
                logger.error(f"Failed to save session metadata: {e}")
        else:
            session_memory.local_metadata[session_id] = json.dumps(metadata)

session_metadata_memory = SessionMetadataMemory()
