import logging
import datetime
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Ticket
from app.repositories import ticket_repo

logger = logging.getLogger("digipay")

class TicketTool:
    @staticmethod
    async def raise_ticket(db: AsyncSession, merchant_id: str, category: str, details: str) -> Dict[str, Any]:
        logger.info(f"Tool API: raise_ticket(merchant_id={merchant_id}, category={category})")
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        new_ticket = Ticket(
            ticket_id=ticket_id,
            merchant_id=merchant_id,
            category=category,
            status="OPEN",
            details=details,
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )
        created = await ticket_repo.create_ticket(db, new_ticket)
        return {
            "ticketId": created.ticket_id,
            "merchantId": created.merchant_id,
            "category": created.category,
            "status": created.status,
            "createdAt": created.created_at.strftime("%Y-%m-%d %H:%M:%S") if created.created_at else None
        }

    @staticmethod
    async def close_ticket(db: AsyncSession, ticket_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: close_ticket(ticket_id={ticket_id})")
        ticket = await ticket_repo.close_ticket(db, ticket_id)
        if not ticket:
            return {"error": f"Ticket '{ticket_id}' not found."}
        return {
            "ticketId": ticket.ticket_id,
            "status": ticket.status,
            "closedAt": ticket.closed_at.strftime("%Y-%m-%d %H:%M:%S") if ticket.closed_at else None
        }
