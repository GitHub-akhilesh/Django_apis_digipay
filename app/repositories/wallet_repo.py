import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select
from app.models.models import Wallet, Transaction
from app.repositories.base_repo import BaseRepository

logger = logging.getLogger("digipay")

class WalletRepository(BaseRepository[Wallet]):
    def __init__(self):
        super().__init__(Wallet)

    async def get_wallet_by_merchant_id(self, db: AsyncSession, merchant_id: str) -> Optional[Wallet]:
        """Query Wallet table safely."""
        try:
            stmt = select(Wallet).where(Wallet.merchant_id == merchant_id)
            res = await db.execute(stmt)
            return res.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"Wallet model query failed for {merchant_id}: {e}")
            return None

    async def get_user_legacy_balance(self, db: AsyncSession, merchant_id: str) -> float:
        """Query legacy balance from DigipayUsers table."""
        try:
            stmt = text("SELECT wallet_balance FROM DigipayUsers WHERE user_id = :m")
            res = await db.execute(stmt, {"m": merchant_id})
            row = res.fetchone()
            if row and row[0] is not None:
                return float(row[0])
        except Exception as e:
            logger.warning(f"DigipayUsers legacy balance lookup failed for {merchant_id}: {e}")
        return 0.0

    async def get_wallet_balances_batch(self, db: AsyncSession, user_ids: List[str]) -> Dict[str, str]:
        """Calculate active balance from ledger transactions table."""
        if not user_ids:
            return {}
        try:
            stmt = text("""
                SELECT user_id, COALESCE(SUM(amount), 0.00) as balance 
                FROM transactions 
                WHERE status IN ('SUCCESS', 'INITIATED') AND user_id IN :u_ids
                GROUP BY user_id
            """)
            res = await db.execute(stmt, {"u_ids": tuple(user_ids)})
            return {row[0]: f"{float(row[1]):.2f}" for row in res.fetchall()}
        except Exception as e:
            logger.error(f"Error calculating ledger balances: {e}")
            return {uid: "0.00" for uid in user_ids}
