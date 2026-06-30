import time
import logging
from typing import Dict
import redis
from app.config import settings

logger = logging.getLogger("digipay.rate_limit")

class RateLimiter:
    def __init__(self):
        self.redis_client = None
        self.use_redis = False
        try:
            # Handle possible env var reference in host (e.g. ${REDIS_HOST})
            redis_host = settings.REDIS_HOST
            if not redis_host or "${" in redis_host:
                redis_host = "127.0.0.1"
                
            self.redis_client = redis.Redis(
                host=redis_host,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                socket_timeout=2.0,
                decode_responses=True
            )
            self.redis_client.ping()
            self.use_redis = True
            logger.info("Connected to Redis successfully for rate limiting.")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to in-memory rate limiting.")
            self.use_redis = False

        # In-memory fallback sliding window store
        self.in_memory_store: Dict[str, list] = {}

    def is_rate_limited(self, key: str, limit: int, window: int) -> bool:
        if self.use_redis and self.redis_client:
            try:
                current_time = time.time()
                key_name = f"rate_limit:{key}"
                pipe = self.redis_client.pipeline()
                # Remove timestamps older than window
                pipe.zremrangebyscore(key_name, 0, current_time - window)
                # Count elements in the set
                pipe.zcard(key_name)
                # Add current request timestamp
                pipe.zadd(key_name, {str(current_time): current_time})
                # Set TTL on the key to clean up space
                pipe.expire(key_name, window)
                
                results = pipe.execute()
                count = results[1]
                
                return count > limit
            except Exception as e:
                logger.error(f"Redis rate limiting query error: {e}. Falling back to in-memory checks.")

        # In-memory sliding window fallback
        current_time = time.time()
        cutoff = current_time - window
        
        if key not in self.in_memory_store:
            self.in_memory_store[key] = []
            
        # Filter out old timestamps
        self.in_memory_store[key] = [t for t in self.in_memory_store[key] if t > cutoff]
        
        # Check limit
        if len(self.in_memory_store[key]) >= limit:
            return True
            
        # Record request timestamp
        self.in_memory_store[key].append(current_time)
        return False

# Global rate limiter instance
rate_limiter = RateLimiter()
