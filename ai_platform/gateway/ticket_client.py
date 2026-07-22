from typing import Optional
from core.config import settings
from core.exceptions import ValidationException
from gateway.base_client import BaseGatewayClient
from gateway.models import TicketResponse, TicketCloseResponse

class TicketClient:
    """
    Typed Resilient SDK Client for the DigiPay Support Ticket microservice.
    """
    def _get_prefix(self) -> str:
        return settings.SERVICE_ENDPOINTS.get("ticket", "/ticket")

    def _validate_merchant_id(self, merchant_id: str):
        if not merchant_id or not merchant_id.strip():
            raise ValidationException("merchant_id parameter must be a non-empty string.")

    def _validate_ticket_id(self, ticket_id: str):
        if not ticket_id or not ticket_id.strip():
            raise ValidationException("ticket_id parameter must be a non-empty string.")

    async def raise_ticket(
        self,
        merchant_id: str,
        category: str,
        details: str,
        jwt_token: Optional[str] = None
    ) -> TicketResponse:
        """Create a support or dispute ticket for the merchant."""
        self._validate_merchant_id(merchant_id)
        if not category or not category.strip():
            raise ValidationException("Category must be a non-empty string.")
        if not details or not details.strip():
            raise ValidationException("Details must be a non-empty string.")
            
        path = f"{self._get_prefix()}/create"
        payload = {
            "merchantId": merchant_id,
            "category": category,
            "details": details
        }
        
        data = await BaseGatewayClient.request_with_resilience(
            method="POST",
            path=path,
            service="ticket",
            operation="raise_ticket",
            merchant_id=merchant_id,
            json_data=payload,
            jwt_token=jwt_token
        )
        return TicketResponse.model_validate(data)

    async def close_ticket(self, ticket_id: str, jwt_token: Optional[str] = None) -> TicketCloseResponse:
        """Close an active support ticket."""
        self._validate_ticket_id(ticket_id)
        path = f"{self._get_prefix()}/close/{ticket_id}"
        
        data = await BaseGatewayClient.request_with_resilience(
            method="POST",
            path=path,
            service="ticket",
            operation="close_ticket",
            txn_id=ticket_id,
            jwt_token=jwt_token
        )
        return TicketCloseResponse.model_validate(data)
