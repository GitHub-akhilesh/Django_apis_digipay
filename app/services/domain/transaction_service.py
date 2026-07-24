import logging
import datetime
import math
import json
import base64
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import txn_repo
from app.utils.helpers import parse_date, build_remarks_from_log, format_txn_memo

logger = logging.getLogger("digipay")

class TransactionService:
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
        from_date = parse_date(from_date_str)
        to_date = parse_date(to_date_str)
        from_datetime = datetime.datetime.combine(from_date, datetime.time.min)
        to_datetime = datetime.datetime.combine(to_date, datetime.time.max)

        total_records, raw_records = await txn_repo.fetch_txn_logs(
            db=db,
            csc_id=csc_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            search_query=search_query,
            rpp=rpp,
            cp=cp,
            txn_type=txn_type
        )

        total_pages = math.ceil(total_records / rpp) if total_records > 0 else 1
        formatted_list = []

        for row in raw_records:
            remarks = build_remarks_from_log(row)
            formatted_memo = format_txn_memo(
                category=str(row.get("category", "")),
                txn_type=str(row.get("type", "")),
                remarks=remarks,
                raw_memo=str(row.get("memo", ""))
            )
            created_at = row.get("date")
            created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(created_at, (datetime.datetime, datetime.date)) else str(created_at or "")

            formatted_list.append({
                "txnId": str(row.get("txn_id", "")),
                "rrn": str(row.get("rrn", "")),
                "mobile": str(row.get("mobile", "")),
                "amount": float(row.get("amount", 0.0)),
                "status": str(row.get("status", "")),
                "type": str(row.get("type", "")),
                "category": str(row.get("category", "")),
                "memo": formatted_memo,
                "createdAt": created_str
            })

        payload = {
            "totalRecords": total_records,
            "totalPages": total_pages,
            "currentPage": cp,
            "recordsPerPage": rpp,
            "list": formatted_list
        }

        json_bytes = json.dumps(payload, default=str).encode('utf-8')
        return base64.b64encode(json_bytes).decode('utf-8')
