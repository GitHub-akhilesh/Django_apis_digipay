import time
import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Optional

from core.exceptions import GatewayException
from gateway.client import GatewayClient

logger = logging.getLogger("ai_platform.gateway.base_client")

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class ServiceCircuitBreaker:
    """
    Per-service Circuit Breaker implementing cooldown and tripping thresholds.
    """
    def __init__(self, name: str, threshold: int = 5, cooldown: float = 10.0):
        self.name = name
        self.threshold = threshold
        self.cooldown = cooldown
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_state_change = time.time()

    def record_success(self):
        self.failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failures += 1
        logger.warning(f"Record Failure on [{self.name}]. Current failures count: {self.failures}")
        if self.failures >= self.threshold:
            if self.state != CircuitState.OPEN:
                logger.error(f"Circuit Breaker [{self.name}] tripped to OPEN state! Failing fast.")
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()

    def check_state(self) -> CircuitState:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_state_change > self.cooldown:
                logger.info(f"Circuit Breaker [{self.name}] cooldown expired. Probing state HALF-OPEN.")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()
        return self.state


class BaseGatewayClient:
    """
    Base client mapping resilient behaviors:
    1. Per-service circuit breaker.
    2. Exponential backoff retries for transient status codes.
    3. Response envelope checks and mapping to GatewayException.
    4. Structured logger execution metrics.
    """
    _breakers: Dict[str, ServiceCircuitBreaker] = {}

    @classmethod
    def _get_breaker(cls, service: str) -> ServiceCircuitBreaker:
        if service not in cls._breakers:
            cls._breakers[service] = ServiceCircuitBreaker(name=service)
        return cls._breakers[service]

    @classmethod
    async def request_with_resilience(
        cls,
        method: str,
        path: str,
        service: str,
        operation: str,
        merchant_id: Optional[str] = None,
        txn_id: Optional[str] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        jwt_token: Optional[str] = None
    ) -> Any:
        breaker = cls._get_breaker(service)
        state = breaker.check_state()
        
        if state == CircuitState.OPEN:
            raise GatewayException("Gateway call blocked: Downstream Service Circuit Breaker is OPEN.")

        retries = 3
        backoff = 0.5
        
        for attempt in range(retries + 1):
            try:
                start_time = time.time()
                response = await GatewayClient.request(
                    method=method,
                    endpoint_path=path,
                    json_data=json_data,
                    params=params,
                    jwt_token=jwt_token
                )
                latency_ms = (time.time() - start_time) * 1000
                status = response.status_code

                # Log trace call details
                logger.info(
                    f"Gateway Call: {method} {path} - Status: {status}",
                    extra={
                        "service": service,
                        "operation": operation,
                        "merchantId": merchant_id,
                        "txnId": txn_id,
                        "latency": latency_ms,
                        "statusCode": status
                    }
                )

                if status >= 400:
                    # Check if transient error
                    if status in [429, 502, 503, 504] and attempt < retries:
                        logger.warning(f"Transient error {status} received. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        breaker.record_failure()
                        raise GatewayException(f"Gateway HTTP error status {status}: {response.text}")

                # Check body structure
                body = response.json()
                if not isinstance(body, dict) or "success" not in body:
                    breaker.record_failure()
                    raise GatewayException("Invalid response envelope structure from downstream microservice.")

                if not body["success"]:
                    # Non-transient business exception. Trip circuit if it's a severe database/service failure,
                    # but for validated business failures, just record success contact and propagate the error.
                    breaker.record_success()
                    raise GatewayException(
                        user_message=body.get("message") or "Gateway business operation failed.",
                        developer_message=body.get("developerMessage")
                    )

                # Reset breaker on successful response contact
                if state == CircuitState.HALF_OPEN:
                    logger.info(f"Circuit Breaker [{service}] successfully probed. Resetting state to CLOSED.")
                
                breaker.record_success()
                return body.get("data")

            except Exception as e:
                if isinstance(e, GatewayException):
                    raise
                if attempt < retries:
                    logger.warning(f"Transient request error: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                else:
                    breaker.record_failure()
                    raise GatewayException(f"Gateway connection failure: {str(e)}") from e
