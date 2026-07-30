"""
HTTP client for the legacy DigiPay API service (`app/main.py`).

Design notes
------------
* The legacy service runs on its own base URL (LEGACY_API_URL) and keeps its
  original `/api/v1/...` paths. Nothing here rewrites a URL.

* Its success envelope is `{"status","msg","errors","resData"}` where `resData`
  is BASE64-encoded JSON (see `app/schemas/schemas.py::EnvelopedResponse`), so
  the payload is decoded here — otherwise the chat layer would render an opaque
  base64 blob at the user.

* Some legacy routes return a bare object instead of the envelope
  (`/wallet_balance` returns a plain cscId→balance map), so both shapes are
  handled.

* Authentication uses the internal-client bypass the legacy AuthMiddleware
  already implements (`X-Client-Id` + `X-Bypass-Secret`). The client id must
  appear in the legacy service's INTERNAL_CLIENTS list.

* Only read endpoints are reachable — see READ_ONLY_ENDPOINTS below.
"""

import base64
import binascii
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import settings
from core.exceptions import AuthenticationException, GatewayException
from gateway.base_client import CircuitState, ServiceCircuitBreaker
from gateway.headers import get_downstream_headers

logger = logging.getLogger("ai_platform.gateway.legacy_v1.client")

# Read-only legacy endpoints the assistant may call, relative to LEGACY_API_PREFIX.
READ_ONLY_ENDPOINTS: Tuple[Tuple[str, str, str], ...] = (
    ("POST", "/txn-logs", "Paginated legacy transaction log search"),
    ("POST", "/passbook", "Paginated legacy passbook entries"),
    ("POST", "/wallet_balance", "Legacy wallet balances for one or more CSC IDs"),
    ("POST", "/get-wallet-balance", "Alias of /wallet_balance"),
)

# Legacy endpoints deliberately NOT exposed to chat, with the reason.
EXCLUDED_ENDPOINTS: Tuple[Tuple[str, str, str, str], ...] = (
    ("POST", "/auth/token", "AUTH", "Issues a JWT access token"),
    ("POST", "/daywise_report", "UNSUPPORTED", "Streams a zip archive, not JSON"),
    ("POST", "/agent/chat", "RECURSION", "The legacy service's own chat agent"),
    ("GET", "/agent/history/{session_id}", "RECURSION", "Legacy agent session history"),
    ("POST", "/agent/test-seed", "WRITE", "Seeds test data"),
    ("GET", "/health", "INTERNAL", "Service health probe, not user-facing data"),
)

_ALLOWED = {(m, p) for m, p, _ in READ_ONLY_ENDPOINTS}


class LegacyV1Client:
    """Resilient, read-only HTTP client for the legacy DigiPay service."""

    _client: Optional[httpx.AsyncClient] = None
    _breaker: Optional[ServiceCircuitBreaker] = None

    # ------------------------------------------------------------- plumbing

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                base_url=settings.LEGACY_API_URL,
                timeout=httpx.Timeout(settings.LEGACY_API_TIMEOUT),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
            )
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None

    @classmethod
    def _get_breaker(cls) -> ServiceCircuitBreaker:
        if cls._breaker is None:
            cls._breaker = ServiceCircuitBreaker(name="legacy_v1")
        return cls._breaker

    @staticmethod
    def _auth_headers(jwt_token: Optional[str]) -> Dict[str, str]:
        """
        Prefer the caller's JWT so the legacy service sees the real end user.
        Fall back to the internal-client bypass for server-initiated calls.
        """
        headers = get_downstream_headers()
        headers["X-Service-Name"] = "AI_PLATFORM"

        if jwt_token:
            headers["Authorization"] = (
                jwt_token if jwt_token.startswith("Bearer ") else f"Bearer {jwt_token}"
            )
        else:
            headers["X-Client-Id"] = settings.LEGACY_INTERNAL_CLIENT_ID
            headers["X-Bypass-Secret"] = settings.INTERNAL_BYPASS_SECRET
        return headers

    @staticmethod
    def _assert_allowed(method: str, path: str):
        """Refuse anything not on the read-only list, before opening a socket."""
        key = (method.upper(), path)
        if key in _ALLOWED:
            return

        for ex_method, ex_path, reason, note in EXCLUDED_ENDPOINTS:
            if ex_method == method.upper() and ex_path == path:
                logger.error(
                    "BLOCKED: chat attempted legacy %s %s (%s: %s)", method, path, reason, note
                )
                raise AuthenticationException(
                    f"Blocked: legacy '{method.upper()} {path}' is excluded from the assistant "
                    f"({reason} — {note})."
                )

        logger.error("BLOCKED: chat attempted unlisted legacy call %s %s", method, path)
        raise AuthenticationException(
            f"Blocked: legacy '{method.upper()} {path}' is not on the read-only allow-list."
        )

    # -------------------------------------------------------------- request

    @classmethod
    async def call(
        cls,
        method: str,
        path: str,
        operation: str,
        json_data: Optional[Dict[str, Any]] = None,
        jwt_token: Optional[str] = None,
    ) -> Any:
        """Call a read-only legacy endpoint and return the decoded payload."""
        cls._assert_allowed(method, path)

        breaker = cls._get_breaker()
        if breaker.check_state() == CircuitState.OPEN:
            raise GatewayException(
                "Legacy DigiPay service call blocked: its circuit breaker is OPEN."
            )

        url = f"{settings.LEGACY_API_PREFIX}{path}"
        payload = {k: v for k, v in (json_data or {}).items() if v is not None}

        try:
            response = await cls._get_client().request(
                method=method, url=url, json=payload, headers=cls._auth_headers(jwt_token)
            )
        except Exception as exc:
            breaker.record_failure()
            raise GatewayException(
                f"Legacy DigiPay service unreachable on {method} {url}: {exc}. "
                f"Is it running at {settings.LEGACY_API_URL}?"
            ) from exc

        logger.info(
            f"Legacy call: {method} {url} - Status: {response.status_code}",
            extra={
                "service": "legacy_v1",
                "operation": operation,
                "merchantId": payload.get("cscId"),
                "statusCode": response.status_code,
            },
        )

        if response.status_code >= 400:
            breaker.record_failure()
            raise GatewayException(
                f"Legacy DigiPay service returned HTTP {response.status_code} on "
                f"{method} {url}: {response.text[:300]}"
            )

        breaker.record_success()
        return cls._unwrap(response, url)

    # -------------------------------------------------------------- parsing

    @classmethod
    def _unwrap(cls, response: httpx.Response, url: str) -> Any:
        try:
            body = response.json()
        except Exception as exc:
            raise GatewayException(
                f"Non-JSON response from legacy service {url}: {response.text[:200]}"
            ) from exc

        # A bare object (e.g. /wallet_balance returns cscId -> balance).
        if not isinstance(body, dict) or "resData" not in body:
            return body

        status = str(body.get("status", "OK")).upper()
        if status not in ("OK", "SUCCESS"):
            raise GatewayException(
                f"Legacy DigiPay service rejected the request → "
                f"{body.get('msg') or 'no message'} {body.get('errors') or ''}".strip()
            )

        return cls._decode_res_data(body.get("resData"), url)

    @staticmethod
    def _decode_res_data(res_data: Any, url: str) -> Any:
        """
        Decode the base64 JSON payload. Anything that is not base64 JSON is
        returned unchanged, so a legacy route that starts sending plain data does
        not break.
        """
        if not isinstance(res_data, str) or not res_data:
            return res_data

        try:
            decoded = base64.b64decode(res_data, validate=True)
        except (binascii.Error, ValueError):
            return res_data

        try:
            return json.loads(decoded.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            logger.warning(f"Legacy resData from {url} decoded but was not JSON; returning raw.")
            return res_data


legacy_v1_client = LegacyV1Client()


def describe_allow_list() -> List[Dict[str, str]]:
    return [
        {
            "method": m,
            "path": f"{settings.LEGACY_API_PREFIX}{p}",
            "summary": s,
            "service": "legacy-digipay-api",
        }
        for m, p, s in READ_ONLY_ENDPOINTS
    ]


def describe_exclusions() -> List[Dict[str, str]]:
    return [
        {
            "method": m,
            "path": f"{settings.LEGACY_API_PREFIX}{p}",
            "reason": reason,
            "note": note,
            "service": "legacy-digipay-api",
        }
        for m, p, reason, note in EXCLUDED_ENDPOINTS
    ]
