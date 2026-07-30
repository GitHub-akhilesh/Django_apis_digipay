import time
import logging
import jwt
from dataclasses import dataclass, field
from typing import List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from auth.identity import (
    extract_merchant_id,
    extract_token,
    extract_user_id,
    normalise_roles,
)
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
        
        # A CORS preflight carries no Authorization header by definition, so
        # authenticating it is impossible: rejecting it with 401 also strips the
        # Access-Control-Allow-* headers, and the browser reports an opaque "CORS
        # error" instead of the real problem. CORS is registered outermost in
        # main.py so preflights should not reach here at all — this is defence in
        # depth in case that ordering is ever changed.
        if request.method == "OPTIONS":
            return await call_next(request)

        # Bypassed paths. /redoc and /docs/oauth2-redirect belong here with /docs:
        # the documentation UIs are public, and omitting /redoc made it 401 while
        # /docs worked, which reads as a broken page rather than a policy.
        bypass_paths = [
            "/", "/ui", "/health", "/ready", "/metrics", "/live", "/favicon.ico",
            "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json",
        ]
        if request.url.path in bypass_paths or request.url.path.startswith("/static"):
            response = await call_next(request)
            return response

        # Extract the token from the Authorization header, a session cookie, or a
        # query parameter. The cookie matters: a DigiPay browser session lives in
        # `access_token`, so header-only extraction saw no credential at all and
        # rejected every request from the React app with 401.
        raw_token = extract_token(request)

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
            
            # A DigiPay token has no cscId/merchantId claim - the CSC ID is in
            # `ownerId` (or `sub`), so resolve across all known spellings.
            # Roles are translated from DigiPay's vocabulary (VLE, ADMIN) into
            # this platform's ROLE_* names; see auth/identity.py.
            user_id = extract_user_id(payload)
            merchant_id = extract_merchant_id(payload)
            roles = normalise_roles(payload.get("roles") or payload.get("authorities"))
            tenant_id = str(payload.get("tenantId") or "")

            # Construct Principal instance
            principal = AuthenticatedPrincipal(
                user_id=user_id,
                merchant_id=merchant_id,
                roles=roles,
                tenant_id=tenant_id
            )
            
            # Attach to request state
            request.state.user = principal

            # Retain the verified raw token so downstream calls can act AS the
            # caller. The DigiPay gateway requires a real end-user JWT — it does
            # not accept internal bypass headers — so without forwarding this,
            # every /v2/* data lookup returns 401 "Full authentication is
            # required" no matter how the caller authenticated to us.
            request.state.access_token = raw_token
            
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
