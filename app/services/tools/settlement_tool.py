import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import settlement_repo

logger = logging.getLogger("digipay")

class SettlementTool:
    @staticmethod
    async def get_settlement_status(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_settlement_status(txn_id={txn_id})")
        stl = await settlement_repo.get_by_txn_id(db, txn_id)
        if not stl:
            return {"status": "not_initiated", "failureReason": "No settlement record found for this transaction."}
        
        date_str = stl.settlement_date.strftime("%Y-%m-%d %H:%M:%S") if stl.settlement_date else None
        return {
            "txnId": stl.txn_id,
            "merchantId": stl.merchant_id,
            "status": stl.status,
            "utr": stl.utr,
            "settlementDate": date_str,
            "failureReason": stl.failure_reason
        }
