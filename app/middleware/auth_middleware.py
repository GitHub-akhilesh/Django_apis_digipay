import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.utils.auth import decode_jwt_token, is_internal_bypass
from app.database import set_tenant_id

logger = logging.getLogger("digipay.auth")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Exclude documentation, assets, health checks, and token endpoints
        if (
            path.startswith("/docs") or 
            path.startswith("/redoc") or 
            path.startswith("/openapi.json") or
            path.startswith("/static") or
            path in ["/api/v1/health", "/api/v1/auth/token", "/"]
        ):
            return await call_next(request)
            
        # Check internal client auth bypass
        if is_internal_bypass(request):
            client_id = request.headers.get("X-Client-Id")
            request.state.user = {"sub": client_id, "role": "internal_client"}
            
            # Use cscId query param or header for tenant ID if available
            tenant_id = request.headers.get("X-Tenant-Id")
            if tenant_id:
                set_tenant_id(tenant_id)
                
            logger.info(f"Authenticated internal service bypass for {client_id}")
            return await call_next(request)
            
        # Standard JWT validation
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "status": "ERROR",
                    "msg": "Missing or invalid authorization header",
                    "errors": ["Missing Authorization Header"],
                    "resData": None
                }
            )
            
        token = auth_header.split(" ")[1]
        try:
            payload = decode_jwt_token(token)
            request.state.user = payload
            
            # Bind the multi-tenant ID context
            tenant_id = payload.get("cscId") or payload.get("tenant_id")
            if tenant_id:
                set_tenant_id(str(tenant_id))
        except Exception as e:
            return JSONResponse(
                status_code=401,
                content={
                    "status": "ERROR",
                    "msg": getattr(e, "detail", "Invalid token signature or expired"),
                    "errors": [str(e)],
                    "resData": None
                }
            )
            
        return await call_next(request)
