import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.domain import WalletSnapshotService

logger = logging.getLogger("digipay")

class WalletTool:
    @staticmethod
    async def get_wallet_balance(
        db: AsyncSession,
        merchant_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        fromDate: Optional[str] = None,
        toDate: Optional[str] = None
    ) -> Dict[str, Any]:
        logger.info(f"Tool API: get_wallet_balance(merchant_id={merchant_id})")
        snapshot = await WalletSnapshotService.get_wallet_snapshot(db, merchant_id)
        start = fromDate or from_date
        end = toDate or to_date
        return {
            "merchantId": snapshot.merchant_id,
            "balance": snapshot.active_balance,
            "oldDigipayBalance": snapshot.legacy_balance,
            "blockedBalance": snapshot.blocked_balance,
            "lastSettlementDate": snapshot.last_settlement_date,
            "lastSettlementAmount": snapshot.last_settlement_amount,
            "fromDate": start,
            "toDate": end
        }

    @staticmethod
    async def get_old_digipay_balance(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_old_digipay_balance(merchant_id={merchant_id})")
        snapshot = await WalletSnapshotService.get_wallet_snapshot(db, merchant_id)
        return {
            "merchantId": merchant_id,
            "oldDigipayBalance": snapshot.legacy_balance,
            "status": "OK"
        }
