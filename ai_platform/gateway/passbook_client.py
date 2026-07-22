from typing import Optional
from core.config import settings
from core.exceptions import ValidationException
from gateway.base_client import BaseGatewayClient
from gateway.models import PassbookResponse

class PassbookClient:
    """
    Typed Resilient SDK Client for the DigiPay Passbook microservice.
    Supports both legacy and modern statement endpoints variants.
    """
    def _validate_merchant_id(self, merchant_id: str):
        if not merchant_id or not merchant_id.strip():
            raise ValidationException("merchant_id parameter must be a non-empty string.")

    async def get_legacy_passbook(self, merchant_id: str, jwt_token: Optional[str] = None) -> PassbookResponse:
        """Fetch transaction history statement entries via the legacy passbook API format."""
        self._validate_merchant_id(merchant_id)
        path = settings.SERVICE_ENDPOINTS.get("legacy_passbook", "/passbook/legacy")
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="passbook",
            operation="legacy_passbook",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return PassbookResponse.model_validate(data)

    async def get_modern_passbook(self, merchant_id: str, jwt_token: Optional[str] = None) -> PassbookResponse:
        """Fetch transaction history statement entries via the modern high-performance passbook API format."""
        self._validate_merchant_id(merchant_id)
        path = settings.SERVICE_ENDPOINTS.get("modern_passbook", "/passbook/modern")
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="passbook",
            operation="modern_passbook",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return PassbookResponse.model_validate(data)

    async def get_passbook(self, merchant_id: str, jwt_token: Optional[str] = None) -> PassbookResponse:
        """Default fetch routing to modern passbook, failing back dynamically to legacy passbook."""
        return await self.get_modern_passbook(merchant_id, jwt_token)
