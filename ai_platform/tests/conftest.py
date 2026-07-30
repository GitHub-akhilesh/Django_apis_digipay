import os
import sys

import pytest

# Standard Python testing pattern: insert parent directory into sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Redis key namespaces the platform writes to. Only these are cleared, so a
# shared Redis instance is never flushed wholesale.
PLATFORM_KEY_PATTERNS = (
    "ai_cache:tool:*",       # services/cache_service.py
    "ai_memory:session:*",   # memory/redis_memory.py
    "ai_memory:metadata:*",  # memory/session.py
    "ai_memory:summary:*",   # memory/summary.py
)


@pytest.fixture(autouse=True)
def isolate_platform_state():
    """
    Clear cached tool results and session memory between tests.

    Read-only tools are cached in Redis with a short TTL. While Redis was
    unreachable this was a silent no-op, but once a real Redis is running (for
    example the docker-compose stack) results leak across tests: one test caches
    a `getTxnLogs` response, and the next test asserting that the gateway was
    called sees a cache hit instead, so its mock is never invoked and the
    assertion fails. The tests were only ever passing because caching was dead.

    Cleared before AND after each test so a leftover key from a previous run
    cannot affect the first test either.
    """
    _clear_platform_keys()
    yield
    _clear_platform_keys()


def _clear_platform_keys():
    try:
        from memory.redis_memory import session_memory
    except Exception:
        return

    client = getattr(session_memory, "redis_client", None)
    if not client or not getattr(session_memory, "use_redis", False):
        # No Redis configured: the in-memory fallback dictionaries are per-process
        # and short-lived, so there is nothing to clear.
        return

    try:
        for pattern in PLATFORM_KEY_PATTERNS:
            keys = list(client.scan_iter(match=pattern, count=500))
            if keys:
                client.delete(*keys)
    except Exception:
        # Never fail a test because cleanup could not reach Redis.
        pass
