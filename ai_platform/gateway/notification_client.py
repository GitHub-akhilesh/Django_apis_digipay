from typing import Optional
from core.config import settings
from core.exceptions import ValidationException
from gateway.base_client import BaseGatewayClient
from gateway.models import NotificationAlertResponse

class NotificationClient:
    """
    Typed Resilient SDK Client for the DigiPay Notification microservice.
    """
    def _get_prefix(self) -> str:
        return settings.SERVICE_ENDPOINTS.get("notification", "/notification")

    def _validate_merchant_id(self, merchant_id: str):
        if not merchant_id or not merchant_id.strip():
            raise ValidationException("merchant_id parameter must be a non-empty string.")

    async def send_alert(
        self,
        merchant_id: str,
        title: str,
        body: str,
        jwt_token: Optional[str] = None
    ) -> NotificationAlertResponse:
        """Dispatch real-time push alerts or notifications to a merchant's active terminal devices."""
        self._validate_merchant_id(merchant_id)
        if not title or not title.strip():
            raise ValidationException("Notification alert title must be a non-empty string.")
        if not body or not body.strip():
            raise ValidationException("Notification alert body must be a non-empty string.")
            
        path = f"{self._get_prefix()}/alert"
        payload = {
            "merchantId": merchant_id,
            "title": title,
            "body": body
        }
        
        data = await BaseGatewayClient.request_with_resilience(
            method="POST",
            path=path,
            service="notification",
            operation="send_alert",
            merchant_id=merchant_id,
            json_data=payload,
            jwt_token=jwt_token
        )
        return NotificationAlertResponse.model_validate(data)
