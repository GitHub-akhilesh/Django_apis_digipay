import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.domain import WalletSnapshotService

logger = logging.getLogger("digipay")

class WalletTool:
    @staticmethod
    async def get_wallet_balance(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_wallet_balance(merchant_id={merchant_id})")
        snapshot = await WalletSnapshotService.get_wallet_snapshot(db, merchant_id)
        return {
            "merchantId": snapshot.merchant_id,
            "balance": snapshot.active_balance,
            "oldDigipayBalance": snapshot.legacy_balance,
            "blockedBalance": snapshot.blocked_balance,
            "lastSettlementDate": snapshot.last_settlement_date,
            "lastSettlementAmount": snapshot.last_settlement_amount
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
