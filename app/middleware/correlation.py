import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.utils.logging import set_correlation_id

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
            
        set_correlation_id(correlation_id)
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
