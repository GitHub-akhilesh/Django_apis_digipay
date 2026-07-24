import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select
from app.models.models import Settlement
from app.repositories.base_repo import BaseRepository

logger = logging.getLogger("digipay")

class SettlementRepository(BaseRepository[Settlement]):
    def __init__(self):
        super().__init__(Settlement)

    async def get_by_txn_id(self, db: AsyncSession, txn_id: str) -> Optional[Settlement]:
        try:
            stmt = select(Settlement).where(Settlement.txn_id == txn_id)
            res = await db.execute(stmt)
            return res.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"Settlement table query failed: {e}")
            return None

    @staticmethod
    async def get_last_payout_from_transactions(
        db: AsyncSession,
        merchant_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Query transactions table directly for legacy system payout/settlement records."""
        try:
            query = """
                SELECT txn_id, amount, status, date, txn_date
                FROM transactions
                WHERE user_id = :csc_id
                  AND (type IN ('Payout', 'Transfer', 'DSP Topup') OR category IN ('PAYOUT', 'TRANSFER', 'Settlement'))
            """
            params = {"csc_id": merchant_id}
            if from_date and to_date:
                query += " AND txn_date BETWEEN :from_date AND :to_date"
                params["from_date"] = from_date
                params["to_date"] = to_date

            query += " ORDER BY date DESC LIMIT 1"

            res = await db.execute(text(query), params)
            row = res.fetchone()
            if row:
                d_str = row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else str(row[4])
                return {
                    "txn_id": row[0],
                    "amount": abs(float(row[1] or 0.0)),
                    "status": row[2],
                    "date": d_str
                }
        except Exception as e:
            logger.warning(f"Error querying last payout from transactions table for {merchant_id}: {e}")
        return None
