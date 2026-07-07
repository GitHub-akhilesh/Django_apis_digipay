import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.utils.rate_limit import rate_limiter
from app.utils.auth import is_internal_bypass
from app.config import settings

logger = logging.getLogger("digipay.rate_limit_middleware")

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Exclude OPTIONS requests, documentation, assets, health checks, and token endpoints
        if (
            request.method == "OPTIONS" or
            path.startswith("/docs") or 
            path.startswith("/redoc") or 
            path.startswith("/openapi.json") or
            path.startswith("/static") or
            path in ["/api/v1/health", "/api/v1/auth/token", "/"]
        ):
            return await call_next(request)
            
        # Bypass rate limiting for validated internal service-to-service requests
        if is_internal_bypass(request):
            return await call_next(request)
            
        # Rate limit by client IP
        client_ip = request.client.host if request.client else "unknown"
        
        limit = settings.RATE_LIMIT
        window = settings.RATE_WINDOW
        
        if rate_limiter.is_rate_limited(client_ip, limit, window):
            logger.warning(f"Rate limit exceeded for IP: {client_ip} on path {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "status": "ERROR",
                    "msg": "Too many requests. Please try again later.",
                    "errors": ["Rate Limit Exceeded"],
                    "resData": None
                },
                headers={"Retry-After": str(window)}
            )
            
        return await call_next(request)
