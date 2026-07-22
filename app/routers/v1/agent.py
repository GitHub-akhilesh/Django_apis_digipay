import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
import redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import get_db, Base, engine
from app.config import settings
from app.services.agent_service import AgentOrchestrator
from app.models.models import Transaction, Merchant, KYC, Wallet, Settlement, Ticket

logger = logging.getLogger("digipay.agent")

router = APIRouter()

# Schema for Chat Request
class AgentChatRequest(BaseModel):
    sessionId: str
    message: str
    cscId: Optional[str] = None

# Schema for Chat Response
class AgentChatResponse(BaseModel):
    status: str
    response: str
    intent: str
    escalate: bool
    confidenceScore: float
    policyChecked: bool

# Initialize Redis client for session storage
redis_client = None
use_redis = False
try:
    redis_host = settings.REDIS_HOST
    if not redis_host or "${" in redis_host:
        redis_host = "127.0.0.1"
    redis_client = redis.Redis(
        host=redis_host,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        socket_timeout=2.0,
        decode_responses=True
    )
    redis_client.ping()
    use_redis = True
    logger.info("Connected to Redis successfully for chat session memory.")
except Exception as e:
    logger.warning(f"Redis connection for chat memory failed: {e}. Falling back to in-memory session store.")
    use_redis = False

# Fallback in-memory storage
in_memory_memory: Dict[str, List[Dict[str, str]]] = {}

def get_session_history(session_id: str) -> List[Dict[str, str]]:
    if use_redis and redis_client:
        try:
            val = redis_client.get(f"agent:session:{session_id}")
            if val:
                return json.loads(val)
        except Exception as e:
            logger.error(f"Redis get history error: {e}")
    return in_memory_memory.get(session_id, [])

def save_session_history(session_id: str, history: List[Dict[str, str]]):
    trimmed_history = history[-10:]
    if use_redis and redis_client:
        try:
            redis_client.setex(
                f"agent:session:{session_id}",
                86400,
                json.dumps(trimmed_history)
            )
            return
        except Exception as e:
            logger.error(f"Redis save history error: {e}")
    in_memory_memory[session_id] = trimmed_history

@router.post("/agent/chat", response_model=AgentChatResponse)
@router.post("/agent/chat/", response_model=AgentChatResponse, include_in_schema=False)
@router.post("/chat", response_model=AgentChatResponse, include_in_schema=False)
@router.post("/chat/", response_model=AgentChatResponse, include_in_schema=False)
async def chat_with_agent(
    req: AgentChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        user = getattr(request.state, "user", None)
        csc_id = None
        if user:
            csc_id = user.get("cscId")
        
        if not csc_id:
            csc_id = req.cscId or "500100100014"

        history = get_session_history(req.sessionId)

        result = await AgentOrchestrator.chat(
            db=db,
            session_id=req.sessionId,
            message=req.message,
            csc_id=csc_id,
            history=history
        )

        new_history = history + [
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": result["response"]}
        ]
        save_session_history(req.sessionId, new_history)

        return AgentChatResponse(
            status="OK",
            response=result["response"],
            intent=result["intent"],
            escalate=result["escalate"],
            confidenceScore=result["confidence_score"],
            policyChecked=result["policy_checked"]
        )
    except Exception as e:
        logger.error(f"Error in chat_with_agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/agent/history/{session_id}")
async def get_agent_history(session_id: str):
    history = get_session_history(session_id)
    return {"sessionId": session_id, "history": history}

@router.post("/agent/test-seed")
async def seed_test_database(db: AsyncSession = Depends(get_db)):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        merchant_id = "500100100014"
        txn_id = "CZUCW178186672384906DQQOQSU69890796"
        
        try:
            await db.execute(text("DELETE FROM tickets"))
            await db.execute(text("DELETE FROM settlements WHERE txn_id = :t"), {"t": txn_id})
            await db.execute(text("DELETE FROM wallets WHERE merchant_id = :m"), {"m": merchant_id})
            await db.execute(text("DELETE FROM kyc_details WHERE merchant_id = :m"), {"m": merchant_id})
            await db.execute(text("DELETE FROM merchants WHERE id = :m"), {"m": merchant_id})
        except Exception as clean_err:
            logger.info(f"Clean table notice: {clean_err}")
        
        merchant = Merchant(
            id=merchant_id,
            name="Akhilesh Mishra",
            phone="9988776655",
            email="akhilesh@digipay.in",
            state="Uttar Pradesh",
            status="ACTIVE",
            bank_name="State Bank of India",
            bank_account_no="30091234567",
            bank_ifsc="SBIN0001234"
        )
        db.add(merchant)

        kyc = KYC(
            merchant_id=merchant_id,
            status="APPROVED",
            pan_number="ABCDE1234F",
            aadhaar_number="333344445555",
            comments="Documents verified manually.",
            updated_at=datetime.utcnow()
        )
        db.add(kyc)

        wallet = Wallet(
            merchant_id=merchant_id,
            balance=Decimal("4560.50"),
            blocked_balance=Decimal("120.00"),
            last_settlement_date=datetime.utcnow() - timedelta(days=1),
            last_settlement_amount=Decimal("1480.00")
        )
        db.add(wallet)

        settlement = Settlement(
            txn_id=txn_id,
            status="auto-reversal-initiated",
            settlement_date=datetime.utcnow() - timedelta(minutes=10),
            utr="UTR887766554433",
            failure_reason="Bank host timeout occurred."
        )
        db.add(settlement)

        await db.flush()
        
        return {"status": "SUCCESS", "msg": "Test database seeded successfully!"}
    except Exception as e:
        logger.error(f"Error seeding database: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
