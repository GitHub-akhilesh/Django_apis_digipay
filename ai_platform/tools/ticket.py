import logging
from gateway import ticket_client
from core.exceptions import ValidationException

logger = logging.getLogger("ai_platform.tools.ticket")

async def raise_ticket(merchant_id: str, category: str, details: str, jwt_token: str = None) -> str:
    """Raise a new dispute or complaint support ticket using the resilient SDK."""
    if not merchant_id or not merchant_id.strip():
        raise ValidationException("merchant_id must be a non-empty string.")
    if not category or not category.strip():
        raise ValidationException("Category must be a non-empty string.")
    if not details or not details.strip():
        raise ValidationException("Details must be a non-empty string.")
        
    res = await ticket_client.raise_ticket(merchant_id.strip(), category.strip(), details.strip(), jwt_token)
    return (
        f"A support ticket {res.ticketId} has been successfully raised under category '{res.category}'. "
        f"Created on: {res.createdAt}. Status: {res.status}."
    )

async def close_ticket(ticket_id: str, jwt_token: str = None) -> str:
    """Close an active support ticket using the resilient SDK."""
    if not ticket_id or not ticket_id.strip():
        raise ValidationException("ticket_id must be a non-empty string.")
        
    res = await ticket_client.close_ticket(ticket_id.strip(), jwt_token)
    return (
        f"Support ticket {res.ticketId} has been successfully marked: {res.status}. "
        f"Closed at: {res.closedAt}."
    )
