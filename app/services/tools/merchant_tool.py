import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import merchant_repo

logger = logging.getLogger("digipay")

class MerchantTool:
    @staticmethod
    async def get_merchant(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_merchant(merchant_id={merchant_id})")
        merchant = await merchant_repo.get_by_merchant_id(db, merchant_id)
        if not merchant:
            return {"error": f"Merchant '{merchant_id}' not found."}
        return {
            "merchantId": merchant.merchant_id,
            "name": merchant.name,
            "mobile": merchant.mobile,
            "status": merchant.status
        }

    @staticmethod
    async def get_bank_account(db: AsyncSession, merchant_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_bank_account(merchant_id={merchant_id})")
        merchant = await merchant_repo.get_by_merchant_id(db, merchant_id)
        if not merchant:
            return {"error": f"Merchant '{merchant_id}' not found."}
        return {
            "merchantId": merchant.merchant_id,
            "bankName": merchant.bank_name or "N/A",
            "bankAccountNo": merchant.bank_account_no or "N/A",
            "bankIfsc": merchant.bank_ifsc or "N/A"
        }
