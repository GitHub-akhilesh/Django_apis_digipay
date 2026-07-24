import logging
import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Ticket
from app.repositories.base_repo import BaseRepository

logger = logging.getLogger("digipay")

class TicketRepository(BaseRepository[Ticket]):
    def __init__(self):
        super().__init__(Ticket)

    async def get_by_ticket_id(self, db: AsyncSession, ticket_id: str) -> Optional[Ticket]:
        stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_ticket(self, db: AsyncSession, ticket: Ticket) -> Ticket:
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        return ticket

    async def close_ticket(self, db: AsyncSession, ticket_id: str) -> Optional[Ticket]:
        ticket = await self.get_by_ticket_id(db, ticket_id)
        if ticket:
            ticket.status = "CLOSED"
            ticket.closed_at = datetime.datetime.now(datetime.timezone.utc)
            await db.commit()
            await db.refresh(ticket)
        return ticket
