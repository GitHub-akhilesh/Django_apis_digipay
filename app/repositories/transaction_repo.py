import logging
import datetime
import math
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select
from app.models.models import Transaction
from app.repositories.base_repo import BaseRepository
from app.utils.validation_utils import get_ledger_table_name

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

    async def fetch_passbook_logs(
        self,
        db: AsyncSession,
        csc_id: str,
        from_datetime: datetime.datetime,
        to_datetime: datetime.datetime,
        search_query: str,
        rpp: int,
        cp: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        table_name = get_ledger_table_name(csc_id)
        offset = (cp - 1) * rpp

        params = {
            "csc_id": csc_id,
            "from_date": from_datetime.strftime("%Y-%m-%d"),
            "to_date": to_datetime.strftime("%Y-%m-%d"),
            "limit": rpp,
            "offset": offset
        }

        search_clause = ""
        if search_query:
            search_clause = "AND (cscTxn LIKE :search OR merchantTxn LIKE :search OR remarks LIKE :search)"
            params["search"] = f"%{search_query}%"

        count_sql = f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE cscId = :csc_id
              AND txnDate BETWEEN :from_date AND :to_date
              {search_clause}
        """

        fetch_sql = f"""
            SELECT *
            FROM {table_name}
            WHERE cscId = :csc_id
              AND txnDate BETWEEN :from_date AND :to_date
              {search_clause}
            ORDER BY sno DESC
            LIMIT :limit OFFSET :offset
        """

        try:
            count_res = await db.execute(text(count_sql), params)
            total_records = count_res.scalar() or 0
            if total_records > 0:
                res = await db.execute(text(fetch_sql), params)
                rows = res.mappings().all()
                ledger_records = []
                for r in rows:
                    r_dict = dict(r)
                    ledger_records.append({
                        "txn_id": r_dict.get("merchantTxn") or r_dict.get("cscTxn", ""),
                        "rrn": r_dict.get("isoRrn", ""),
                        "amount": float(r_dict.get("walletTxnAmount") or r_dict.get("txnAmount") or 0.0),
                        "type": r_dict.get("txnType") or "Transaction",
                        "category": str(r_dict.get("categoryId") or "AEPS"),
                        "memo": r_dict.get("remarks", ""),
                        "status": "SUCCESS" if r_dict.get("flag") == 0 or not r_dict.get("status") else str(r_dict.get("status")),
                        "date": str(r_dict.get("creationDate") or r_dict.get("txnDate") or ""),
                        "running_balance": float(r_dict.get("walletBalance") or 0.0)
                    })
                return total_records, ledger_records
        except Exception as e:
            logger.info(f"Ledger table {table_name} query fallback to transactions table for {csc_id}: {e}")

        return await self.fetch_txn_logs(
            db=db,
            csc_id=csc_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            search_query=search_query,
            rpp=rpp,
            cp=cp,
            txn_type="ALL"
        )
