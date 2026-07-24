import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Settlement
from app.repositories.base_repo import BaseRepository

logger = logging.getLogger("digipay")

class SettlementRepository(BaseRepository[Settlement]):
    def __init__(self):
        super().__init__(Settlement)

    async def get_by_txn_id(self, db: AsyncSession, txn_id: str) -> Optional[Settlement]:
        stmt = select(Settlement).where(Settlement.txn_id == txn_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
