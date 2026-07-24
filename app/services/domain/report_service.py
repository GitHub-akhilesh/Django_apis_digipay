import logging
import io
import zipfile
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings

logger = logging.getLogger("digipay")

class ReportService:
    @staticmethod
    async def get_daywise_report(
        db: AsyncSession,
        csc_id: str,
        year_month: str,
        day: str = None
    ) -> Tuple[bytes, str]:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            report_name = f"daywise_report_{csc_id}_{year_month}.csv"
            csv_content = f"Date,CSC_ID,Total_Transactions,Total_Volume\n2026-06-01,{csc_id},12,15450.00\n"
            zip_file.writestr(report_name, csv_content)
        
        zip_buffer.seek(0)
        zip_name = f"Daywise_Report_{year_month}.zip" if not day else f"Daywise_Report_{year_month}_{day}.zip"
        return zip_buffer.getvalue(), zip_name
