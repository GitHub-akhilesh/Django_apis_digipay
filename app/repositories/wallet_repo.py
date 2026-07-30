import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, bindparam
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

    # Sentinel used by the reference implementation for a CSC ID that has no
    # transaction rows. Kept verbatim: callers may match on this string.
    BALANCE_UNAVAILABLE = "Wallet balance not available"

    # A CSC ID list is bounded upstream in the reference; mirrored here so a
    # runaway request cannot build an unbounded IN clause.
    MAX_CSC_IDS = 100

    async def get_wallet_balances_batch(
        self,
        db: AsyncSession,
        user_ids: List[str],
        write_back: bool = True,
    ) -> Dict[str, str]:
        """
        Wallet balance per CSC ID, summed from the transactions table.

        Ported from the authoritative implementation,
        CSC_Connect_Digipay/mainapp/digipay_utils.py::cal_wallet_balance:

            SELECT COALESCE(SUM(amount), 0) AS wallet_balance FROM transactions
            WHERE status IN ('SUCCESS', 'INITIATED') AND user_id = %s

        Three differences from the previous version here, each of which changed
        the answer:

        1. A CSC ID with no matching rows was dropped entirely by GROUP BY, so the
           response omitted it and callers inferred zero. The reference reports
           BALANCE_UNAVAILABLE, which is not the same claim as a zero balance.
        2. Any SQL error returned "0.00" for every ID — presenting a database
           failure as a real balance of zero. It now reports the sentinel instead.
        3. The reference writes the computed balance back to
           DigipayUsers.wallet_balance / balance_update_at, so the cached column
           other consumers read stays in step. That write is a cache refresh, not
           a financial mutation; pass write_back=False to skip it.

        The return shape is unchanged: {cscId: "amount-as-string"}.
        """
        if not user_ids:
            return {}

        ids = [str(u).strip() for u in user_ids if str(u).strip()]
        if not ids:
            return {}
        if len(ids) > self.MAX_CSC_IDS:
            raise ValueError(
                f"You must provide between 1 and {self.MAX_CSC_IDS} CSC IDs "
                f"(received {len(ids)})."
            )

        # Start from the sentinel so an ID absent from the result set is reported
        # as unavailable rather than silently missing or zero.
        balances: Dict[str, str] = {uid: self.BALANCE_UNAVAILABLE for uid in ids}

        try:
            stmt = text("""
                SELECT user_id, COALESCE(SUM(amount), 0) AS wallet_balance
                FROM transactions
                WHERE status IN ('SUCCESS', 'INITIATED') AND user_id IN :u_ids
                GROUP BY user_id
            """).bindparams(bindparam("u_ids", expanding=True))
            res = await db.execute(stmt, {"u_ids": ids})
            for row in res.fetchall():
                user_id, amount = row[0], row[1]
                if user_id is None:
                    continue
                balances[str(user_id)] = (
                    f"{Decimal(str(amount)):.2f}" if amount is not None
                    else self.BALANCE_UNAVAILABLE
                )
        except Exception as e:
            # Do not fabricate "0.00" here: a query failure is not a zero balance.
            logger.error(f"Error calculating ledger balances for {ids}: {e}", exc_info=True)
            return balances

        if write_back:
            await self._cache_balances(db, balances)

        return balances

    async def _cache_balances(self, db: AsyncSession, balances: Dict[str, str]) -> None:
        """
        Refresh DigipayUsers.wallet_balance / balance_update_at.

        Best-effort by design: the caller asked for a balance, so a failure to
        update the cached column must not fail the read. Skips sentinel values so
        an unavailable balance is never written as a number.
        """
        writable = {
            uid: value for uid, value in balances.items()
            if value != self.BALANCE_UNAVAILABLE
        }
        if not writable:
            return

        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            stmt = text(
                "UPDATE DigipayUsers SET wallet_balance = :bal, balance_update_at = :ts "
                "WHERE user_id = :uid"
            )
            for uid, value in writable.items():
                await db.execute(stmt, {"bal": value, "ts": update_time, "uid": uid})
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not cache wallet balances on DigipayUsers: {e}")
            try:
                await db.rollback()
            except Exception:
                pass
