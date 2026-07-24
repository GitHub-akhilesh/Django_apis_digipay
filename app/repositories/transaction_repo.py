import logging
import datetime
import math
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select
from app.models.models import Transaction
from app.repositories.base_repo import BaseRepository

logger = logging.getLogger("digipay")

class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self):
        super().__init__(Transaction)

    async def get_by_txn_id(self, db: AsyncSession, txn_id: str) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.txn_id == txn_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def fetch_txn_logs(
        self,
        db: AsyncSession,
        csc_id: str,
        from_datetime: datetime.datetime,
        to_datetime: datetime.datetime,
        search_query: str,
        rpp: int,
        cp: int,
        txn_type: str
    ) -> Tuple[int, List[Dict[str, Any]]]:
        offset = (cp - 1) * rpp

        type_filter_clause = "type NOT IN ('Bio Auth', 'Bio auth', 'Cash Deposit Advice(Cash Deposit)')"
        params = {
            "csc_id": csc_id,
            "from_date": from_datetime,
            "to_date": to_datetime,
            "limit": rpp,
            "offset": offset
        }

        if txn_type and txn_type != "ALL":
            if txn_type == "AEPS_CASH_WITHDRAWAL":
                type_filter_clause += " AND (category = 'AEPS' AND type = 'Cash Withdrawal')"
            elif txn_type == "AEPS_MINI_STATEMENT":
                type_filter_clause += " AND (category = 'AEPS' AND type = 'Mini Statement')"
            elif txn_type == "PAYOUT":
                type_filter_clause += " AND (category = 'PAYOUT' OR type = 'Payout')"
            elif txn_type == "DSP_TOPUP":
                type_filter_clause += " AND (category = 'DSP_TOPUP' OR type = 'DSP Topup')"
            else:
                type_filter_clause += " AND (category = :txn_type_filter OR type = :txn_type_filter)"
                params["txn_type_filter"] = str(txn_type)

        search_clause = ""
        if search_query:
            search_clause = "AND (txn_id LIKE :search OR rrn LIKE :search OR mobile LIKE :search OR memo LIKE :search)"
            params["search"] = f"%{search_query}%"

        count_sql = f"""
            SELECT COUNT(*)
            FROM transactions
            WHERE user_id = :csc_id
              AND date BETWEEN :from_date AND :to_date
              AND {type_filter_clause}
              {search_clause}
        """
        try:
            count_res = await db.execute(text(count_sql), params)
            total_records = count_res.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting transactions in repository: {e}")
            total_records = 0

        fetch_sql = f"""
            SELECT *
            FROM transactions
            WHERE user_id = :csc_id
              AND date BETWEEN :from_date AND :to_date
              AND {type_filter_clause}
              {search_clause}
            ORDER BY date DESC, id DESC
            LIMIT :limit OFFSET :offset
        """
        try:
            res = await db.execute(text(fetch_sql), params)
            rows = res.mappings().all()
            records = [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching transaction rows in repository: {e}")
            records = []

        return total_records, records
