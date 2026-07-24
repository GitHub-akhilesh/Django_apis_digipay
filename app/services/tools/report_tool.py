import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings

logger = logging.getLogger("digipay")

class ReportTool:
    @staticmethod
    async def get_daywise_report(db: AsyncSession, merchant_id: str, year_month: str = "2026 June", day: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Tool API: get_daywise_report(merchant_id={merchant_id}, year_month={year_month}, day={day})")
        download_url = f"{settings.DOWNLOAD_BASE_URL}/daywise_report?year_month={year_month}"
        if day:
            download_url += f"&day={day}"
        return {
            "merchantId": merchant_id,
            "yearMonth": year_month,
            "day": day,
            "status": "READY",
            "downloadUrl": download_url
        }

    @staticmethod
    async def get_aeps_status(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_aeps_status(txn_id={txn_id})")
        return {"txnId": txn_id, "service": "AEPS", "status": "SUCCESS", "gatewayCode": "00"}

    @staticmethod
    async def get_matm_status(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_matm_status(txn_id={txn_id})")
        return {"txnId": txn_id, "service": "MATM", "status": "SUCCESS", "gatewayCode": "00"}
