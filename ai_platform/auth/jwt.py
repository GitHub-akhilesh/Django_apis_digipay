import jwt
import logging
from typing import Dict, Any
from core.config import settings

logger = logging.getLogger("ai_platform.auth.jwt")

class AuthManager:
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Decodes and validates a JWT token using configuration settings.
        Propagates specific jwt exceptions (ExpiredSignatureError, PyJWTError).
        """
        options = {}
        if not settings.JWT_ISSUER:
            options["verify_iss"] = False
        if not settings.JWT_AUDIENCE:
            options["verify_aud"] = False

        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options=options,
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE
        )
        
        # Ensure subject/cscId context is present
        csc_id = payload.get("cscId") or payload.get("sub") or payload.get("userId")
        if not csc_id:
            raise jwt.PyJWTError("Token missing subject/cscId/userId identity claims.")
        
        logger.info(f"Successfully authenticated JWT for cscId: {csc_id}")
        return payload

    @staticmethod
    def get_csc_id_from_ws_token(token: str) -> str:
        """Helper to extract cscId context directly, defaulting to test id if auth is bypassed in LOCAL."""
        if not token or token == "test_token_bypass":
            if settings.ENV == "LOCAL" or settings.ENV == "TEST":
                logger.info("Auth bypass enabled: Using default test cscId context '500100100014'")
                return "500100100014"
        payload = AuthManager.verify_token(token)
        return str(payload.get("cscId") or payload.get("sub") or payload.get("userId") or "500100100014")

    @staticmethod
    def get_roles_from_ws_token(token: str) -> list:
        """Helper to extract roles list directly, defaulting to ROLE_MERCHANT if auth is bypassed in LOCAL."""
        if not token or token == "test_token_bypass":
            if settings.ENV == "LOCAL" or settings.ENV == "TEST":
                return ["ROLE_MERCHANT"]
        try:
            payload = AuthManager.verify_token(token)
            roles = payload.get("roles") or payload.get("authorities") or ["ROLE_MERCHANT"]
            return roles if isinstance(roles, list) else [str(roles)]
        except Exception:
            return ["ROLE_MERCHANT"]
