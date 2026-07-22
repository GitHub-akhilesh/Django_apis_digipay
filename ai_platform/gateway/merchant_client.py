from typing import Optional
from core.config import settings
from core.exceptions import ValidationException
from gateway.base_client import BaseGatewayClient
from gateway.models import MerchantProfileResponse, MerchantStatusResponse

class MerchantClient:
    """
    Typed Resilient SDK Client for the DigiPay Merchant microservice.
    """
    def _get_prefix(self) -> str:
        return settings.SERVICE_ENDPOINTS.get("merchant", "/merchant")

    def _validate_merchant_id(self, merchant_id: str):
        if not merchant_id or not merchant_id.strip():
            raise ValidationException("merchant_id parameter must be a non-empty string.")

    async def get_profile(self, merchant_id: str, jwt_token: Optional[str] = None) -> MerchantProfileResponse:
        """Fetch profile details for the specified merchant."""
        self._validate_merchant_id(merchant_id)
        path = f"{self._get_prefix()}/profile"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="merchant",
            operation="profile",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return MerchantProfileResponse.model_validate(data)

    async def get_status(self, merchant_id: str, jwt_token: Optional[str] = None) -> MerchantStatusResponse:
        """Fetch regulatory, compliance, and active status for the specified merchant."""
        self._validate_merchant_id(merchant_id)
        path = f"{self._get_prefix()}/status"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="merchant",
            operation="status",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return MerchantStatusResponse.model_validate(data)
