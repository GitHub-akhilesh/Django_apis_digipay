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
            await self._reset_session(db)
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
            await self._reset_session(db)
        return 0.0

    @staticmethod
    async def _reset_session(db: AsyncSession) -> None:
        """
        Roll back after a swallowed query error.

        These lookups are optional -- a missing `wallets` or `DigipayUsers`
        table must not fail the request, because the transactions-table
        fallback can still answer it. But an aborted statement leaves the
        session unusable, so without this every *later* query in the same
        request fails too and the fallback never gets its chance.
        """
        try:
            await db.rollback()
        except Exception:
            pass

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
        Wallet balance per CSC ID.

        Ported from the authoritative implementation,
        CSC_Connect_Digipay/mainapp/digipay_utils.py::cal_wallet_balance, which
        is a refresh-then-read against DigipayUsers -- not a read of the
        transactions table:

        1. UPDATE DigipayUsers.wallet_balance from SUM(transactions.amount) for
           the requested IDs. The inner JOIN means only IDs that actually have
           transaction rows are refreshed.
        2. SELECT user_id, wallet_balance FROM DigipayUsers for those IDs, and
           return that.

        Reading step 2 from DigipayUsers rather than from the SUM is what makes
        the sentinel mean the right thing. BALANCE_UNAVAILABLE is reported when
        the CSC ID is absent from DigipayUsers, or its wallet_balance is NULL --
        i.e. we have no balance on record. A VLE who is on file with a balance
        of zero and simply has no transactions still gets "0.00", because
        DigipayUsers holds that zero. Computing the answer from the SUM instead
        collapses those two cases and turns a legitimate "0.00" into the
        sentinel, changing what the endpoint returns to the frontend.

        A SQL failure also yields the sentinel rather than "0.00": a database
        error is not a balance of zero.

        write_back=False skips the step-1 refresh and reads the stored value
        as-is. The return shape is unchanged: {cscId: "amount-as-string"}.
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

        # Start from the sentinel so an ID absent from DigipayUsers is reported
        # as unavailable rather than silently missing or zero.
        balances: Dict[str, str] = {uid: self.BALANCE_UNAVAILABLE for uid in ids}

        if write_back:
            await self._refresh_cached_balances(db, ids)

        try:
            stmt = text("""
                SELECT user_id, wallet_balance
                FROM DigipayUsers
                WHERE user_id IN :u_ids
            """).bindparams(bindparam("u_ids", expanding=True))
            res = await db.execute(stmt, {"u_ids": ids})
            for row in res.fetchall():
                user_id, wallet_balance = row[0], row[1]
                if user_id is None:
                    continue
                balances[str(user_id)] = (
                    str(Decimal(str(wallet_balance)))
                    if wallet_balance is not None
                    else self.BALANCE_UNAVAILABLE
                )
        except Exception as e:
            # Do not fabricate "0.00" here: a query failure is not a zero balance.
            logger.error(f"Error reading wallet balances for {ids}: {e}", exc_info=True)
            await self._reset_session(db)

        return balances

    async def _refresh_cached_balances(self, db: AsyncSession, ids: List[str]) -> None:
        """
        Refresh DigipayUsers.wallet_balance / balance_update_at from the ledger.

        This is step 1 of the reference implementation, kept as a single
        set-based UPDATE ... JOIN so it matches that statement exactly. The
        inner join restricts the refresh to CSC IDs that have transaction rows;
        everyone else keeps whatever balance is already on record.

        Best-effort by design: the caller asked for a balance, so a failure to
        refresh the cached column must not fail the read that follows.
        """
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            stmt = text("""
                UPDATE DigipayUsers du
                JOIN (
                    SELECT user_id, COALESCE(SUM(amount), 0) AS total
                    FROM transactions
                    WHERE status IN ('SUCCESS', 'INITIATED') AND user_id IN :u_ids
                    GROUP BY user_id
                ) t ON du.user_id = t.user_id
                SET du.wallet_balance = t.total,
                    du.balance_update_at = :ts
            """).bindparams(bindparam("u_ids", expanding=True))
            await db.execute(stmt, {"u_ids": ids, "ts": update_time})
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not refresh wallet balances on DigipayUsers: {e}")
            await self._reset_session(db)
