"""
Resilient client for the DigiPay Spring Boot gateway-service.

The gateway returns `com.digipay.common.bos.CommonResponseBO`:

    { "status": "OK" | "VAR" | "ERR",
      "msg": "...",
      "errors": [ {"field": "...", "message": "..."} ],
      "resData": <payload> }

which is a DIFFERENT envelope from the `{"success": bool, "data": ...}` shape
that `gateway.base_client.BaseGatewayClient` handles. This module therefore sits
alongside it rather than replacing it, so the pre-existing DigiPay integrations
keep working byte-for-byte as before.

Every call is checked against the read-only allow-list in `gateway.v2.safety`
before a socket is opened.
"""

import asyncio
import base64
import binascii
import json
import logging
import time
from typing import Any, Dict, Optional

from core.config import settings
from core.exceptions import (
    GatewayException,
    UpstreamSessionException,
    ValidationException,
)
from gateway.base_client import CircuitState, ServiceCircuitBreaker
from gateway.client import GatewayClient
from gateway.v2.safety import resolve_endpoint

logger = logging.getLogger("ai_platform.gateway.v2.base")

TRANSIENT_STATUS_CODES = (429, 502, 503, 504)


class GatewayV2Response:
    """Parsed CommonResponseBO."""

    def __init__(self, status: str, msg: Optional[str], res_data: Any, errors: Any):
        self.status = (status or "ERR").upper()
        self.msg = msg
        self.res_data = res_data
        self.errors = errors or []

    @property
    def ok(self) -> bool:
        return self.status == "OK"

    @property
    def validation_failed(self) -> bool:
        return self.status == "VAR" or bool(self.errors)

    def error_text(self) -> str:
        if self.errors:
            details = "; ".join(
                f"{e.get('field', 'field')}: {e.get('message', 'invalid')}"
                for e in self.errors
                if isinstance(e, dict)
            )
            if details:
                return f"{self.msg or 'Validation failed'} ({details})"
            # Errors present but not field/message shaped - show them verbatim
            # rather than discarding the only diagnostic available.
            return f"{self.msg or 'Rejected'} ({self.errors})"

        if self.msg:
            return self.msg

        # An empty msg with a non-OK status leaves nothing to act on, so include
        # the status and any payload. "The DigiPay gateway rejected the request"
        # on its own gave no clue that /v2/txn/logs was missing a required field.
        detail = f"status={self.status}"
        if self.res_data not in (None, "", {}, []):
            detail += f", resData={str(self.res_data)[:200]}"
        return f"The DigiPay gateway rejected the request ({detail})."


class GatewayV2Client:
    """
    Shared transport for all read-only gateway-service calls.

    Applies: allow-list enforcement, per-service circuit breaking, exponential
    backoff on transient HTTP status codes, and CommonResponseBO unwrapping.
    """

    _breakers: Dict[str, ServiceCircuitBreaker] = {}

    @classmethod
    def _get_breaker(cls, service: str) -> ServiceCircuitBreaker:
        # Namespaced so a v2 outage does not trip the legacy client's breaker.
        name = f"v2:{service}"
        if name not in cls._breakers:
            cls._breakers[name] = ServiceCircuitBreaker(name=name)
        return cls._breakers[name]

    @staticmethod
    def prefix(service: str) -> str:
        prefix = settings.V2_SERVICE_ENDPOINTS.get(service)
        if not prefix:
            raise ValidationException(
                f"No gateway prefix configured for service '{service}'. "
                f"Known services: {sorted(settings.V2_SERVICE_ENDPOINTS)}"
            )
        return prefix

    @staticmethod
    def _prune(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Drop None values so the Spring validators only see supplied fields."""
        if payload is None:
            return None
        return {k: v for k, v in payload.items() if v is not None}

    @classmethod
    async def call(
        cls,
        method: str,
        path: str,
        service: str,
        operation: str,
        csc_id: Optional[str] = None,
        txn_id: Optional[str] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        jwt_token: Optional[str] = None,
        retries: int = 2,
    ) -> Any:
        """
        Execute a read-only gateway call and return the unwrapped `resData`.

        Raises AuthenticationException when the endpoint is not allow-listed,
        GatewayException on transport failure or a non-OK CommonResponseBO.
        """
        # 1. Read-only enforcement — raises before any network activity.
        resolve_endpoint(method, path)

        breaker = cls._get_breaker(service)
        if breaker.check_state() == CircuitState.OPEN:
            raise GatewayException(
                f"Gateway call blocked: circuit breaker for '{service}' is OPEN."
            )

        json_data = cls._prune(json_data)
        params = cls._prune(params)
        backoff = 0.5

        for attempt in range(retries + 1):
            try:
                started = time.time()
                response = await GatewayClient.request(
                    method=method,
                    endpoint_path=path,
                    json_data=json_data,
                    params=params,
                    headers=headers,
                    jwt_token=jwt_token,
                )
                latency_ms = (time.time() - started) * 1000
                status_code = response.status_code

                logger.info(
                    f"Gateway V2 call: {method} {path} - Status: {status_code}",
                    extra={
                        "service": f"v2:{service}",
                        "operation": operation,
                        "merchantId": csc_id,
                        "txnId": txn_id,
                        "latency": latency_ms,
                        "statusCode": status_code,
                    },
                )

                if status_code in (401, 403):
                    # The caller's session, not a platform fault. The gateway
                    # holds server-side session state and answers "Session
                    # expired" once it lapses even for a structurally valid JWT,
                    # so this must not be reported as an outage or escalated -
                    # the user simply needs to sign in again. Retrying and
                    # tripping the breaker would both be wrong here.
                    breaker.record_success()
                    raise UpstreamSessionException(
                        f"DigiPay gateway rejected the session on {method} {path}: "
                        f"{response.text[:200]}"
                    )

                if status_code >= 400:
                    if status_code in TRANSIENT_STATUS_CODES and attempt < retries:
                        logger.warning(
                            f"Transient {status_code} on {operation}. Retrying in {backoff}s..."
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    breaker.record_failure()
                    raise GatewayException(
                        f"Gateway HTTP {status_code} on {method} {path}: {response.text[:400]}"
                    )

                parsed = cls._parse(response, path)

                if not parsed.ok:
                    # A business/validation rejection means the gateway is healthy;
                    # record contact so one bad filter does not trip the breaker.
                    breaker.record_success()
                    raise GatewayException(
                        f"{operation} rejected by gateway → {parsed.error_text()}"
                    )

                breaker.record_success()
                return parsed.res_data

            except (GatewayException, UpstreamSessionException):
                raise
            except Exception as exc:
                if attempt < retries:
                    logger.warning(f"Transient request error on {operation}: {exc}. Retrying...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                breaker.record_failure()
                raise GatewayException(
                    f"Gateway connection failure on {method} {path}: {exc}"
                ) from exc

        raise GatewayException(f"Gateway call {method} {path} exhausted all retries.")

    @classmethod
    def _parse(cls, response, path: str) -> GatewayV2Response:
        try:
            body = response.json()
        except Exception as exc:
            raise GatewayException(
                f"Non-JSON response from gateway {path}: {response.text[:200]}"
            ) from exc

        if not isinstance(body, dict):
            raise GatewayException(
                f"Unexpected response shape from gateway {path}: expected a CommonResponseBO object."
            )

        # Tolerate the alternate `{success, data}` envelope in case a route is
        # served by the Python API layer rather than the Spring gateway.
        if "status" not in body and "success" in body:
            return GatewayV2Response(
                status="OK" if body.get("success") else "ERR",
                msg=body.get("message"),
                res_data=cls._decode_res_data(body.get("data")),
                errors=body.get("errors"),
            )

        return GatewayV2Response(
            status=body.get("status"),
            msg=body.get("msg") or body.get("message"),
            res_data=cls._decode_res_data(body.get("resData", body.get("data"))),
            errors=body.get("errors"),
        )

    @staticmethod
    def _decode_res_data(res_data: Any) -> Any:
        """
        Decode base64-encoded JSON payloads.

        Several gateway controllers return `resData` as base64 JSON rather than a
        plain object — /v2/txn/logs, /v2/ledger/passbook and /v2/device/list all
        do. The React app handles this with `decodeParams` (atob + JSON.parse);
        without the same step here, chat rendered the raw base64 at the user, e.g.
        "eyJkZXZpY2VzIjpbXSwiY3NjSWQiOiI1MDAxMDAxMDAwMTQifQ==" as the device list.

        Anything that is not base64 JSON is returned untouched, so a controller
        that sends a plain object keeps working.
        """
        if not isinstance(res_data, str) or len(res_data) < 8:
            return res_data

        try:
            decoded = base64.b64decode(res_data, validate=True)
        except (binascii.Error, ValueError):
            return res_data

        try:
            text = decoded.decode("utf-8")
        except UnicodeDecodeError:
            return res_data

        try:
            return json.loads(text)
        except ValueError:
            # Base64 of a plain string (not JSON) - return the decoded text.
            return text if text.isprintable() else res_data
