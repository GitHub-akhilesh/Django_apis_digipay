from typing import Optional
from core.config import settings
from core.exceptions import ValidationException
from gateway.base_client import BaseGatewayClient
from gateway.models import AEPSBalanceResponse, AEPSWithdrawalResponse

class AEPSClient:
    """
    Typed Resilient SDK Client for the Aadhaar Enabled Payment System (AEPS) microservice.
    """
    def _get_prefix(self) -> str:
        return settings.SERVICE_ENDPOINTS.get("aeps", "/aeps")

    def _validate_merchant_id(self, merchant_id: str):
        if not merchant_id or not merchant_id.strip():
            raise ValidationException("merchant_id parameter must be a non-empty string.")

    def _validate_txn_id(self, txn_id: str):
        if not txn_id or not txn_id.strip():
            raise ValidationException("txn_id parameter must be a non-empty string.")

    async def balance_enquiry(self, merchant_id: str, jwt_token: Optional[str] = None) -> AEPSBalanceResponse:
        """Perform an AEPS balance query via the Aadhaar NPCI network."""
        self._validate_merchant_id(merchant_id)
        path = f"{self._get_prefix()}/balance"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="POST",
            path=path,
            service="aeps",
            operation="balance",
            merchant_id=merchant_id,
            params={"merchantId": merchant_id},
            jwt_token=jwt_token
        )
        return AEPSBalanceResponse.model_validate(data)

    async def cash_withdrawal_status(self, txn_id: str, jwt_token: Optional[str] = None) -> AEPSWithdrawalResponse:
        """Query the status of an ongoing or completed AEPS cash withdrawal transaction."""
        self._validate_txn_id(txn_id)
        path = f"{self._get_prefix()}/withdrawal/status/{txn_id}"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="GET",
            path=path,
            service="aeps",
            operation="withdrawal_status",
            txn_id=txn_id,
            jwt_token=jwt_token
        )
        return AEPSWithdrawalResponse.model_validate(data)
