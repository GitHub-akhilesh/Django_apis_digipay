import logging
from services.cache_service import cache_service

logger = logging.getLogger("ai_platform.chaos.redis_failure")

class RedisFailureSimulator:
    def __init__(self):
        self._original_get = cache_service.get_cached_result
        self._original_set = cache_service.set_cached_result

    def inject_failure(self):
        """Simulate Redis connection dropouts by making cache get/set raise exceptions."""
        logger.warning("Injecting Redis Failure Chaos...")
        def raise_conn_error(*args, **kwargs):
            raise ConnectionError("Redis cluster connection timed out (Simulated Chaos)")
        
        cache_service.get_cached_result = raise_conn_error
        cache_service.set_cached_result = raise_conn_error

    def recover(self):
        """Restore original caching functions."""
        logger.info("Recovering Redis Connection...")
        cache_service.get_cached_result = self._original_get
        cache_service.set_cached_result = self._original_set

redis_failure_simulator = RedisFailureSimulator()
