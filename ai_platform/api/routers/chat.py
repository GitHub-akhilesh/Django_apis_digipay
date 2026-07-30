import logging
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel

from services.chat_service import chat_service
from core.responses import ApiResponse
from core.validators import sanitize_message_input

logger = logging.getLogger("ai_platform.api.routers.chat")
router = APIRouter(prefix="/api/v1", tags=["REST Chat"])

class ChatRequest(BaseModel):
    """
    Simplified chat request payload containing only session identifiers and user messages.
    All user identity claims are securely derived from request context.
    """
    sessionId: str
    message: str

@router.post("/chat")
async def http_chat(req: ChatRequest, request: Request):
    """REST chat client endpoint resolving caller context from security middleware principal."""
    # 1. Input sanitization
    clean_message = sanitize_message_input(req.message)
    
    # 2. Extract authenticated principal claims
    principal = getattr(request.state, "user", None)
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security context is unauthenticated. Request state missing user principal."
        )

    # 3. Delegate execution to ChatService.
    #
    # The caller's verified token is forwarded so downstream calls act AS the
    # user. This is required, not an optimisation: the DigiPay gateway rejects
    # internal bypass headers and answers 401 "Full authentication is required"
    # without a real end-user JWT, so passing None here made every /v2/* data
    # lookup fail. It also means the gateway's own RBAC and audit trail see the
    # actual user rather than a service account.
    result = await chat_service.process_chat_message(
        session_id=req.sessionId,
        message=clean_message,
        csc_id=principal.merchant_id,
        user_roles=principal.roles,
        jwt_token=getattr(request.state, "access_token", None)
    )
    
    # 4. Return via Global Response Builder
    return ApiResponse.respond_success(
        data={
            "response": result["response"],
            "intent": result["intent"],
            "escalate": result["escalate"],
            "policyChecked": result["policyChecked"]
        },
        message="Chat request processed successfully."
    )

from fastapi.responses import StreamingResponse
from streaming.manager import stream_manager

@router.post("/chat/stream")
async def http_chat_stream(req: ChatRequest, request: Request):
    """Server-Sent Events (SSE) streaming chat endpoint emitting real-time progress events."""
    clean_message = sanitize_message_input(req.message)
    principal = getattr(request.state, "user", None)
    csc_id = principal.merchant_id if principal else "500100100014"
    roles = principal.roles if principal else ["ROLE_MERCHANT"]

    history = await chat_service.get_session_history(req.sessionId)
    
    return StreamingResponse(
        stream_manager.generate_chat_stream(
            session_id=req.sessionId,
            message=clean_message,
            csc_id=csc_id,
            history=history,
            user_roles=roles,
            # Same reason as the non-streaming endpoint: the gateway needs the
            # caller's real JWT or every data lookup comes back 401.
            jwt_token=getattr(request.state, "access_token", None)
        ),
        media_type="text/event-stream"
    )
