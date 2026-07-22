import time
import logging
import jwt
from dataclasses import dataclass, field
from typing import List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from auth.jwt import AuthManager
from core.error_codes import ErrorCode
from core.responses import ApiResponse
from core.validators import validate_jwt_format
from monitoring.mdc import (
    TraceContext,
    user_id_var,
    merchant_id_var,
    latency_var,
    status_code_var
)

logger = logging.getLogger("ai_platform.auth.middleware")

@dataclass
class AuthenticatedPrincipal:
    """
    Represents the authenticated caller principal extracted from JWT signatures.
    Attached to request.state.user for downstream router access.
    """
    user_id: str
    merchant_id: str
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    tenant_id: str = ""

class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Bypassed paths
        bypass_paths = ["/", "/ui", "/health", "/ready", "/metrics", "/docs", "/openapi.json", "/live", "/favicon.ico"]
        if request.url.path in bypass_paths or request.url.path.startswith("/static"):
            response = await call_next(request)
            return response

        # Extract JWT Token from headers or query parameters
        auth_header = request.headers.get("Authorization")
        raw_token = None
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ")[1]
        else:
            raw_token = request.query_params.get("token")

        if not raw_token:
            logger.warning(f"Rejecting unauthenticated call to endpoint: {request.url.path}")
            status_code_var.set(401)
            duration = time.time() - start_time
            latency_var.set(duration)
            
            return ApiResponse.respond_error(
                error_code=ErrorCode.AUTH_MISSING_TOKEN,
                developer_message="Authorization token is missing.",
                status_code=401
            )
            
        try:
            # 1. Format-level string validation (max size, ASCII characters)
            token = validate_jwt_format(raw_token)
            
            # 2. Cryptographic signature and claims validation
            payload = AuthManager.verify_token(token)
            
            user_id = str(payload.get("sub") or payload.get("userId") or "")
            merchant_id = str(payload.get("cscId") or payload.get("merchantId") or "")
            roles = payload.get("roles") or payload.get("authorities") or []
            tenant_id = str(payload.get("tenantId") or "")
            
            # Construct Principal instance
            principal = AuthenticatedPrincipal(
                user_id=user_id,
                merchant_id=merchant_id,
                roles=roles if isinstance(roles, list) else [str(roles)],
                tenant_id=tenant_id
            )
            
            # Attach to request state
            request.state.user = principal
            
            # Bind context variables directly via TraceContext.process_txn()
            TraceContext.process_txn(
                merchant_id=principal.merchant_id,
                user_id=principal.user_id
            )
            
        except jwt.ExpiredSignatureError as e:
            logger.warning(f"JWT signature verification failed (Expired): {e}")
            status_code_var.set(401)
            duration = time.time() - start_time
            latency_var.set(duration)
            return ApiResponse.respond_error(
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                developer_message=f"Expired authentication signature context: {str(e)}",
                status_code=401
            )
        except jwt.PyJWTError as e:
            logger.warning(f"JWT signature verification failed (Cryptographic): {e}")
            status_code_var.set(401)
            duration = time.time() - start_time
            latency_var.set(duration)
            return ApiResponse.respond_error(
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                developer_message=f"Invalid authentication signature context: {str(e)}",
                status_code=401
            )
        except Exception as e:
            # Re-raise format / validation errors or bubble unexpected ones
            # If they are AuthenticationException subclasses, bubble up to global handler
            logger.error(f"Authentication exception encountered: {e}")
            status_code_var.set(401)
            duration = time.time() - start_time
            latency_var.set(duration)
            return ApiResponse.respond_error(
                error_code=ErrorCode.AUTH_INVALID_TOKEN,
                developer_message=f"Format validation exception: {str(e)}",
                status_code=401
            )

        try:
            response: Response = await call_next(request)
            status_code_var.set(response.status_code)
        finally:
            # Clear business transaction context
            TraceContext.clear()
            
            duration = time.time() - start_time
            latency_var.set(duration)
            
        return response
