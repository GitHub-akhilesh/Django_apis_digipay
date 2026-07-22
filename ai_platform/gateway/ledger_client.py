from typing import Optional
from core.config import settings
from core.exceptions import ValidationException
from gateway.base_client import BaseGatewayClient
from gateway.models import LedgerStatementResponse

class LedgerClient:
    """
    Typed Resilient SDK Client for the DigiPay Ledger microservice.
    """
    def _get_prefix(self) -> str:
        return settings.SERVICE_ENDPOINTS.get("ledger", "/ledger")

    def _validate_merchant_id(self, merchant_id: str):
        if not merchant_id or not merchant_id.strip():
            raise ValidationException("merchant_id parameter must be a non-empty string.")

    async def get_ledger(self, merchant_id: str, jwt_token: Optional[str] = None) -> LedgerStatementResponse:
        """Fetch general double-entry statement statement summaries for the specified merchant."""
        self._validate_merchant_id(merchant_id)
        path = f"{self._get_prefix()}/statement"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="ledger",
            operation="statement",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return LedgerStatementResponse.model_validate(data)
