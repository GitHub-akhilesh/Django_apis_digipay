import time
import logging
import httpx
from typing import Dict, Any, Optional

from core.config import settings
from gateway.headers import get_downstream_headers
from gateway.auth import get_internal_auth_headers

logger = logging.getLogger("ai_platform.gateway.client")

class GatewayClient:
    """
    HTTP Client for calling Spring Boot microservices.
    Maintains a reusable connection pool and automatically attaches B3 tracing headers
    (X-B3-TraceId, X-B3-SpanId, X-Correlation-ID, X-Service-Name) to ensure participation
    in end-to-end distributed traces.
    """
    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Returns or instantiates the singleton connection-pooled AsyncClient."""
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.API_GATEWAY_TIMEOUT),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
            )
        return cls._client

    @classmethod
    async def close(cls):
        """Closes the underlying client connection pool during application shutdown."""
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None

    @staticmethod
    def _prepare_headers(
        extra_headers: Optional[Dict[str, str]] = None,
        jwt_token: Optional[str] = None
    ) -> Dict[str, str]:
        # 1. Fetch active B3 propagation headers
        headers = get_downstream_headers(extra_headers)
        headers["X-Service-Name"] = "AI_PLATFORM"
        
        # 2. Add authorization or internal bypass headers
        if jwt_token:
            bare_token = jwt_token[7:].strip() if jwt_token.startswith("Bearer ") else jwt_token
            headers["Authorization"] = f"Bearer {bare_token}"

            # The DigiPay gateway reads the session from the `access_token`
            # cookie, NOT from the Authorization header. The two rejections are
            # distinguishable and prove it: a Bearer header yields "Full
            # authentication is required to access this resource" (credential not
            # recognised at all), while the cookie yields "Session expired"
            # (recognised, server session lapsed). Sending only the header meant
            # every /v2/* call was unauthenticated no matter how valid the token.
            if settings.GATEWAY_FORWARD_TOKEN_AS_COOKIE:
                cookie_name = settings.GATEWAY_TOKEN_COOKIE_NAME
                existing = headers.get("Cookie")
                cookie = f"{cookie_name}={bare_token}"
                headers["Cookie"] = f"{existing}; {cookie}" if existing else cookie
        else:
            headers.update(get_internal_auth_headers())

        return headers

    @classmethod
    async def request(
        cls,
        method: str,
        endpoint_path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        jwt_token: Optional[str] = None
    ) -> httpx.Response:
        # gateway_base_url normalises the /gateway context path, so API_GATEWAY_URL
        # may be given with or without it.
        target_url = (
            f"{settings.gateway_base_url}{endpoint_path}"
            if not endpoint_path.startswith("http")
            else endpoint_path
        )
        final_headers = cls._prepare_headers(headers, jwt_token)
        
        logger.info(f"Calling downstream gateway endpoint: {method} {target_url}")
        client = cls.get_client()
        
        try:
            response = await client.request(
                method=method,
                url=target_url,
                json=json_data,
                params=params,
                headers=final_headers
            )
            return response
        except Exception as e:
            logger.error(f"Downstream gateway call failed: {method} {target_url} - Error: {e}")
            raise

    @classmethod
    async def get(cls, endpoint_path: str, params=None, headers=None, jwt_token=None):
        return await cls.request("GET", endpoint_path, params=params, headers=headers, jwt_token=jwt_token)

    @classmethod
    async def post(cls, endpoint_path: str, json_data=None, headers=None, jwt_token=None):
        return await cls.request("POST", endpoint_path, json_data=json_data, headers=headers, jwt_token=jwt_token)

    @classmethod
    async def put(cls, endpoint_path: str, json_data=None, headers=None, jwt_token=None):
        return await cls.request("PUT", endpoint_path, json_data=json_data, headers=headers, jwt_token=jwt_token)

    @classmethod
    async def delete(cls, endpoint_path: str, headers=None, jwt_token=None):
        return await cls.request("DELETE", endpoint_path, headers=headers, jwt_token=jwt_token)
