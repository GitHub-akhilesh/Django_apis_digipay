import logging
import datetime
import json
import base64
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import txn_repo
from app.services.domain import TransactionService, PassbookService
from app.utils.helpers import parse_date
from app.config import settings

logger = logging.getLogger("digipay")

class TransactionTool:
    @staticmethod
    async def get_transaction(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: get_transaction(txn_id={txn_id})")
        txn = await txn_repo.get_by_txn_id(db, txn_id)
        if not txn:
            return {"error": f"Transaction '{txn_id}' not found."}
        
        date_str = txn.date.strftime("%Y-%m-%d %H:%M:%S") if txn.date else None
        return {
            "txnId": txn.txn_id,
            "merchantId": txn.user_id,
            "amount": float(txn.amount or 0.0),
            "status": txn.status,
            "type": txn.type,
            "category": txn.category,
            "date": date_str,
            "utr": txn.rrn or "N/A",
            "failureReason": txn.memo if txn.status == "FAILED" else None,
            "settlementStatus": "auto-reversal-initiated" if txn.status == "FAILED" else "completed"
        }

    @staticmethod
    async def check_refund_eligibility(db: AsyncSession, txn_id: str) -> Dict[str, Any]:
        logger.info(f"Tool API: check_refund_eligibility(txn_id={txn_id})")
        txn = await txn_repo.get_by_txn_id(db, txn_id)
        if not txn:
            return {"eligible": False, "reason": "Transaction ID not found."}
        if txn.status == "FAILED":
            return {"eligible": True, "amount": float(txn.amount or 0.0), "reason": "Transaction failed, auto-reversal eligible."}
        return {"eligible": False, "amount": float(txn.amount or 0.0), "reason": "Transaction is already successful or settled."}

    @staticmethod
    async def get_txn_logs(db: AsyncSession, merchant_id: str, from_date: str, to_date: str, txn_type: str = "ALL", search: str = "") -> Dict[str, Any]:
        logger.info(f"Tool API: get_txn_logs(merchant_id={merchant_id})")
        try:
            from_dt = parse_date(from_date)
            to_dt = parse_date(to_date)
        except Exception:
            to_dt = datetime.date.today()
            from_dt = to_dt - datetime.timedelta(days=30)

        res_b64 = await TransactionService.get_txn_logs(
            db=db,
            csc_id=merchant_id,
            from_date_str=from_dt.strftime("%d-%m-%Y"),
            to_date_str=to_dt.strftime("%d-%m-%Y"),
            search_query=search,
            rpp=10,
            cp=1,
            txn_type=txn_type
        )
        try:
            decoded = json.loads(base64.b64decode(res_b64).decode('utf-8'))
            total_records = decoded.get("totalRecords", 0)
            records = decoded.get("list", [])
        except Exception:
            total_records = 0
            records = []

        return {
            "merchantId": merchant_id,
            "fromDate": from_dt.strftime("%Y-%m-%d"),
            "toDate": to_dt.strftime("%Y-%m-%d"),
            "totalRecords": total_records,
            "records": records[:5]
        }

    @staticmethod
    async def generate_statement(db: AsyncSession, merchant_id: str, from_date: str, to_date: str) -> Dict[str, Any]:
        logger.info(f"Tool API: generate_statement(merchant_id={merchant_id}, from={from_date}, to={to_date})")
        try:
            from_dt = parse_date(from_date)
            to_dt = parse_date(to_date)
        except Exception:
            to_dt = datetime.date.today()
            from_dt = to_dt - datetime.timedelta(days=30)

        res_b64 = await PassbookService.get_passbook(
            db=db,
            csc_id=merchant_id,
            from_date_str=from_dt.strftime("%d-%m-%Y"),
            to_date_str=to_dt.strftime("%d-%m-%Y"),
            search_query="",
            rpp=10,
            cp=1
        )
        try:
            decoded = json.loads(base64.b64decode(res_b64).decode('utf-8'))
            total_records = decoded.get("totalRecords", 0)
            records = decoded.get("list", [])
        except Exception:
            total_records = 0
            records = []

        total_volume = sum(float(r.get("lgrAmt") or r.get("amount") or 0.0) for r in records)
        download_file_url = f"{settings.DOWNLOAD_BASE_URL}/statements/stmt_{merchant_id}_{from_date}_to_{to_date}.pdf"

        return {
            "merchantId": merchant_id,
            "fromDate": from_dt.strftime("%Y-%m-%d"),
            "toDate": to_dt.strftime("%Y-%m-%d"),
            "totalTransactions": total_records,
            "totalVolume": total_volume,
            "downloadUrl": download_file_url,
            "sampleRecords": records[:3]
        }
