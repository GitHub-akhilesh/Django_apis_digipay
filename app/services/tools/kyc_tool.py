import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import kyc_repo

logger = logging.getLogger("digipay")

class KYCTool:
    @staticmethod
    async def get_kyc_status(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_kyc_status(merchant_id={merchant_id})")
        kyc = await kyc_repo.get_by_merchant_id(db, merchant_id)
        if not kyc:
            return {"status": "PENDING", "comments": "KYC record not initialized."}
        return {
            "merchantId": kyc.merchant_id,
            "status": kyc.status,
            "comments": kyc.rejection_reason or kyc.comments
        }
