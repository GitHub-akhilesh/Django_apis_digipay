import json
import logging
from typing import Dict, Any, Optional
from memory.redis_memory import session_memory

logger = logging.getLogger("ai_platform.services.cache_service")

class CacheService:
    @staticmethod
    def get_cache_key(tool_name: str, args: Dict[str, Any]) -> str:
        args_str = json.dumps(args, sort_keys=True)
        return f"ai_cache:tool:{tool_name}:{args_str}"

    def get_cached_result(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Fetch cached data from Redis if available."""
        if not session_memory.use_redis or not session_memory.redis_client:
            return None
            
        cache_key = self.get_cache_key(tool_name, args)
        try:
            cached_val = session_memory.redis_client.get(cache_key)
            if cached_val:
                logger.info(f"Cache HIT for tool {tool_name}")
                return cached_val
        except Exception as e:
            logger.warning(f"Cache fetch failed: {e}")
        return None

    def set_cached_result(self, tool_name: str, args: Dict[str, Any], result: str, ttl: int = 30):
        """Cache tool results into Redis."""
        if not session_memory.use_redis or not session_memory.redis_client:
            return
            
        cache_key = self.get_cache_key(tool_name, args)
        try:
            session_memory.redis_client.setex(cache_key, ttl, result)
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

cache_service = CacheService()
