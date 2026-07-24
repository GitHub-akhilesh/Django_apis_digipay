import logging
import os
import zipfile
import io
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import FileResponse
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import LogsRequest, PassbookRequest, EnvelopedResponse, TokenRequest, TokenResponse, WalletBalanceRequest, DaywiseReportRequest
from app.services.services import DigipayService
from app.utils.auth import create_jwt_token

logger = logging.getLogger("digipay.endpoints")


router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "OK", "msg": "API service is healthy"}

@router.post("/auth/token", response_model=TokenResponse)
async def generate_auth_token(req: TokenRequest):
    """
    Test endpoint to generate a JWT access token for authentication.
    Pass a cscId in the body to bind the token to that user context.
    """
    csc_id = req.cscId or "500100100014"
    token_data = {"sub": req.username, "cscId": csc_id}
    access_token = create_jwt_token(token_data)
    logger.info(f"Generated test token for user: {req.username}, cscId: {csc_id}")
    return TokenResponse(access_token=access_token)

@router.post("/txn-logs", response_model=EnvelopedResponse)
async def get_transaction_logs(
    req: LogsRequest, 
    db: AsyncSession = Depends(get_db),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id", description="Internal Client ID (e.g. WALLET_SERVICE)"),
    x_bypass_secret: Optional[str] = Header(None, alias="X-Bypass-Secret", description="Internal Client Bypass Secret")
):
    try:
        base64_data = await DigipayService.get_txn_logs(
            db=db,
            csc_id=req.cscId,
            from_date_str=req.fromDate,
            to_date_str=req.toDate,
            search_query=req.search,
            rpp=req.rpp,
            cp=req.cp,
            txn_type=req.type
        )
        
        # Dynamically format the success message based on transaction type
        if req.type == "AEPS_CASH_WITHDRAWAL":
            msg = "AePS Cash Withdrawal logs fetched successfully!"
        else:
            formatted_type = req.type.replace("_", " ").title()
            msg = f"{formatted_type} logs fetched successfully!"
            
        return EnvelopedResponse(
            status="OK",
            msg=msg,
            errors=None,
            resData=base64_data
        )
    except Exception as e:
        logger.error(f"Error fetching txn logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to fetch transaction logs. Please verify parameters and try again."
        )

@router.post("/passbook", response_model=EnvelopedResponse)
async def get_passbook(
    req: PassbookRequest, 
    db: AsyncSession = Depends(get_db),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id", description="Internal Client ID (e.g. WALLET_SERVICE)"),
    x_bypass_secret: Optional[str] = Header(None, alias="X-Bypass-Secret", description="Internal Client Bypass Secret")
):
    try:
        base64_data = await DigipayService.get_passbook(
            db=db,
            csc_id=req.cscId,
            from_date_str=req.fromDate,
            to_date_str=req.toDate,
            search_query=req.search,
            rpp=req.rpp,
            cp=req.cp
        )
        return EnvelopedResponse(
            status="OK",
            msg="success",
            errors=None,
            resData=base64_data
        )
    except Exception as e:
        logger.error(f"Error fetching passbook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to fetch passbook records. Please verify parameters and try again."
        )


@router.post("/get-wallet-balance")
@router.post("/wallet_balance")
async def get_wallet_balance(
    req: WalletBalanceRequest, 
    db: AsyncSession = Depends(get_db),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id", description="Internal Client ID (e.g. WALLET_SERVICE)"),
    x_bypass_secret: Optional[str] = Header(None, alias="X-Bypass-Secret", description="Internal Client Bypass Secret")
):
    """
    Retrieves wallet balances for a list of CSC IDs.
    Returns a dictionary mapping cscId to balance.
    """
    try:
        if not req.csc_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing csc_ids"
            )
        balances = await DigipayService.get_wallet_balances(db, req.csc_ids)
        return balances
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching wallet balance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/daywise_report")
async def monthly_daywise_report(
    req: DaywiseReportRequest,
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id", description="Internal Client ID (e.g. WALLET_SERVICE)"),
    x_bypass_secret: Optional[str] = Header(None, alias="X-Bypass-Secret", description="Internal Client Bypass Secret")
):
    """
    Serves consolidated monthly zip report or extracts and serves daywise zip archive.
    """
    try:
        parts = req.year_month.split()
        if len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format must be 'YYYY MonthName', e.g. '2026 June'"
            )
        year, month = parts[0], parts[1]
        
        # Check standard report directories
        base_dir = "reports"
        if not os.path.exists(os.path.join(base_dir, year)):
            if os.path.exists(os.path.join("/home/akhilesh/reports", year)):
                base_dir = "/home/akhilesh/reports"
            elif os.path.exists(os.path.join("/home/akhilesh/digipay_api/reports", year)):
                base_dir = "/home/akhilesh/digipay_api/reports"
                
        month_zip_path = os.path.join(base_dir, year, f"{month}.zip")
        if not os.path.exists(month_zip_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found for this month."
            )
            
        if not req.day:
            return FileResponse(month_zip_path, media_type="application/zip", filename=f"{month}.zip")
            
        with zipfile.ZipFile(month_zip_path, 'r') as month_zip:
            day_zip_name = f"{req.day}.zip"
            if day_zip_name not in month_zip.namelist():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found for this day."
                )
            
            day_zip_data = month_zip.read(day_zip_name)
            buffer = io.BytesIO(day_zip_data)
            
            from fastapi.responses import StreamingResponse
            buffer.seek(0)
            return StreamingResponse(
                buffer, 
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={day_zip_name}"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching daywise report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Exception occurred, please try again later."
        )
