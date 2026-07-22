from typing import Optional
from core.config import settings
from core.exceptions import ValidationException
from gateway.base_client import BaseGatewayClient
from gateway.models import WalletBalanceResponse, WalletLimitsResponse, WalletDetailsResponse

class WalletClient:
    """
    Typed Resilient SDK Client for the DigiPay Wallet microservice.
    """
    def _get_prefix(self) -> str:
        return settings.SERVICE_ENDPOINTS.get("wallet", "/wallet")

    def _validate_merchant_id(self, merchant_id: str):
        if not merchant_id or not merchant_id.strip():
            raise ValidationException("merchant_id parameter must be a non-empty string.")

    async def get_balance(self, merchant_id: str, jwt_token: Optional[str] = None) -> WalletBalanceResponse:
        """Fetch the wallet balance of the specified merchant."""
        self._validate_merchant_id(merchant_id)
        path = f"{self._get_prefix()}/balance"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="wallet",
            operation="balance",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return WalletBalanceResponse.model_validate(data)

    async def get_limits(self, merchant_id: str, jwt_token: Optional[str] = None) -> WalletLimitsResponse:
        """Fetch transaction limits of the specified merchant."""
        self._validate_merchant_id(merchant_id)
        path = f"{self._get_prefix()}/limits"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="wallet",
            operation="limits",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return WalletLimitsResponse.model_validate(data)

    async def get_wallet(self, merchant_id: str, jwt_token: Optional[str] = None) -> WalletDetailsResponse:
        """Fetch structural details of the merchant's wallet."""
        self._validate_merchant_id(merchant_id)
        path = f"{self._get_prefix()}/details"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="wallet",
            operation="details",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return WalletDetailsResponse.model_validate(data)
