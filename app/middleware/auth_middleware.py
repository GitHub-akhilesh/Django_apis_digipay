import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.utils.auth import decode_jwt_token, is_internal_bypass
from app.database import set_tenant_id

logger = logging.getLogger("digipay.auth")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = str(request.url.path).lower()
        
        # 1. Immediately bypass auth for all SDK files and Demo UI
        if "sdk" in path or path.startswith("/sdk"):
            return await call_next(request)

        # 2. Exclude OPTIONS requests, documentation, assets, health checks, chat endpoints, and public endpoints
        if (
            request.method == "OPTIONS" or
            "docs" in path or
            "redoc" in path or
            "openapi" in path or
            "static" in path or
            "agent" in path or
            "health" in path or
            "token" in path or
            path == "/"
        ):
            return await call_next(request)
            
        # Check internal client auth bypass
        if is_internal_bypass(request):
            client_id = (request.headers.get("X-Client-Id") or request.headers.get("x-client-id") or "INTERNAL_CLIENT").strip()
            request.state.user = {"sub": client_id, "role": "internal_client"}
            
            # Use cscId query param or header for tenant ID if available
            tenant_id = (request.headers.get("X-Tenant-Id") or request.headers.get("x-tenant-id") or "").strip()
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
