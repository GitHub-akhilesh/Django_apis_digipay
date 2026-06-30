import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.schemas import LogsRequest, PassbookRequest, EnvelopedResponse, TokenRequest, TokenResponse
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
async def get_transaction_logs(req: LogsRequest, db: AsyncSession = Depends(get_db)):
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
            detail=str(e)
        )

@router.post("/passbook", response_model=EnvelopedResponse)
async def get_passbook(req: PassbookRequest, db: AsyncSession = Depends(get_db)):
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
            detail=str(e)
        )
