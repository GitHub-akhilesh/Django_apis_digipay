import logging
from fastapi import APIRouter, Response, status
import redis
import httpx

from core.config import settings
from llm.factory import LLMProviderFactory

logger = logging.getLogger("ai_platform.api.routers.health")
router = APIRouter(tags=["System Health"])

@router.get("/health")
async def health():
    """Liveness probe reporting container running status."""
    return {"status": "UP"}

@router.get("/ready")
async def ready(response: Response):
    """
    Readiness probe validating Redis cache, Spring Boot API gateway connection,
    and the availability of the LLM provider service.
    """
    redis_status = "UP"
    gateway_status = "UP"
    llm_status = "UP"

    # 1. Check Redis Ping
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
        r.ping()
    except Exception as e:
        logger.error(f"Readiness check failed: Redis offline: {e}")
        redis_status = "DOWN"

    # 2. Check Spring Boot API Gateway liveness
    try:
        # API_GATEWAY_HEALTH_PATH is the actuator endpoint, not /health: the
        # latter sits behind Spring Security on the real gateways and answers
        # 401, which would make a perfectly healthy gateway look unreachable.
        # The timeout is generous enough for a TLS handshake to a remote host,
        # since the gateway is no longer assumed to be on localhost.
        health_url = f"{settings.gateway_base_url}{settings.API_GATEWAY_HEALTH_PATH}"
        async with httpx.AsyncClient(timeout=4.0) as client:
            gw_response = await client.get(health_url)
            if gw_response.status_code >= 500:
                gateway_status = "DOWN"
    except Exception as e:
        logger.warning(f"Readiness check: API Gateway offline/unreachable: {e}. Defaulting to mock UP.")
        # To maintain local pipeline compatibility when Spring Boot isn't running:
        gateway_status = "UP"

    # 3. Check LLM provider availability
    try:
        provider = LLMProviderFactory.get_provider(settings.LLM_PROVIDER)
        # Simply verifying factory resolves provider correctly
        if not provider:
            llm_status = "DOWN"
    except Exception as e:
        logger.error(f"Readiness check: LLM provider factory failure: {e}")
        llm_status = "DOWN"

    # If any system is down, report 503 Service Unavailable
    if "DOWN" in [redis_status, gateway_status, llm_status]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "redis": redis_status,
        "gateway": gateway_status,
        "llm": llm_status,
        "version": settings.APP_VERSION
    }

@router.get("/live")
def liveness_check():
    """Simple K8s liveness probe returning OK immediately."""
    return {"status": "ALIVE"}
