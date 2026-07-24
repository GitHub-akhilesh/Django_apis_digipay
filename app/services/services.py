import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.domain import WalletSnapshotService, TransactionService, PassbookService, ReportService
from app.repositories import wallet_repo

logger = logging.getLogger("digipay")

class DigipayService:
    """Facade for DigiPay domain services."""

    @staticmethod
    async def get_wallet_balances(db: AsyncSession, user_ids: List[str]) -> Dict[str, str]:
        return await wallet_repo.get_wallet_balances_batch(db, user_ids)

    @staticmethod
    async def get_txn_logs(
        db: AsyncSession,
        csc_id: str,
        from_date_str: str,
        to_date_str: str,
        search_query: str,
        rpp: int,
        cp: int,
        txn_type: str
    ) -> str:
        return await TransactionService.get_txn_logs(
            db, csc_id, from_date_str, to_date_str, search_query, rpp, cp, txn_type
        )

    @staticmethod
    async def get_passbook(
        db: AsyncSession,
        csc_id: str,
        from_date_str: str,
        to_date_str: str,
        search_query: str,
        rpp: int,
        cp: int
    ) -> str:
        return await PassbookService.get_passbook(
            db, csc_id, from_date_str, to_date_str, search_query, rpp, cp
        )

    @staticmethod
    async def get_daywise_report(
        db: AsyncSession,
        csc_id: str,
        year_month: str,
        day: str = None
    ):
        return await ReportService.get_daywise_report(db, csc_id, year_month, day)
