import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import KYC
from app.repositories.base_repo import BaseRepository

logger = logging.getLogger("digipay")

class KYCRepository(BaseRepository[KYC]):
    def __init__(self):
        super().__init__(KYC)

    async def get_by_merchant_id(self, db: AsyncSession, merchant_id: str) -> Optional[KYC]:
        try:
            stmt = select(KYC).where(KYC.merchant_id == merchant_id)
            res = await db.execute(stmt)
            return res.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"KYC query failed for {merchant_id}: {e}")
            return None
