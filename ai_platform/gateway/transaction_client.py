from typing import Optional
from core.config import settings
from core.exceptions import ValidationException
from gateway.base_client import BaseGatewayClient
from gateway.models import TransactionResponse, TransactionListResponse

class TransactionClient:
    """
    Typed Resilient SDK Client for the DigiPay Transaction microservice.
    """
    def _get_prefix(self) -> str:
        return settings.SERVICE_ENDPOINTS.get("transaction", "/transaction")

    def _validate_merchant_id(self, merchant_id: str):
        if not merchant_id or not merchant_id.strip():
            raise ValidationException("merchant_id parameter must be a non-empty string.")

    def _validate_txn_id(self, txn_id: str):
        if not txn_id or not txn_id.strip():
            raise ValidationException("txn_id parameter must be a non-empty string.")

    async def get_transaction(self, txn_id: str, jwt_token: Optional[str] = None) -> TransactionResponse:
        """Fetch details of a single transaction by its transaction ID."""
        self._validate_txn_id(txn_id)
        path = f"{self._get_prefix()}/{txn_id}"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="transaction",
            operation="get_transaction",
            txn_id=txn_id,
            jwt_token=jwt_token
        )
        return TransactionResponse.model_validate(data)

    async def search(
        self,
        merchant_id: str,
        limit: int = 10,
        jwt_token: Optional[str] = None
    ) -> TransactionListResponse:
        """Query and search past transactions for a given merchant."""
        self._validate_merchant_id(merchant_id)
        path = f"{self._get_prefix()}/search"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="transaction",
            operation="search",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id, "limit": limit},
            jwt_token=jwt_token
        )
        return TransactionListResponse.model_validate(data)

    async def reverse(self, txn_id: str, jwt_token: Optional[str] = None) -> TransactionResponse:
        """Trigger an idempotent transaction reversal or cancellation request."""
        self._validate_txn_id(txn_id)
        path = f"{self._get_prefix()}/reverse/{txn_id}"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="POST",
            path=path,
            service="transaction",
            operation="reverse",
            txn_id=txn_id,
            jwt_token=jwt_token
        )
        return TransactionResponse.model_validate(data)
