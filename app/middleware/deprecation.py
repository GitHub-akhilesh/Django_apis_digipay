import logging
import datetime
import hashlib
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.config import settings

logger = logging.getLogger("digipay.deprecation")

class DeprecationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
            
        path = request.url.path
        rules = settings.API_DEPRECATION_RULES_JSON or {}
        
        matched_rule = None
        matched_pattern = None
        for pattern, rule in rules.items():
            # Match exact or starting path
            if path == pattern or path.startswith(pattern):
                matched_rule = rule
                matched_pattern = pattern
                break
                
        if matched_rule:
            sunset_str = matched_rule.get("sunset")
            block_after_sunset = matched_rule.get("block", True)
            
            if sunset_str:
                try:
                    sunset_date = datetime.datetime.strptime(sunset_str, "%Y-%m-%d").date()
                except ValueError:
                    sunset_date = None
                    
                if sunset_date:
                    current_date = datetime.date.today()
                    
                    # 1. Post-Sunset Blocking
                    if current_date > sunset_date:
                        if block_after_sunset and settings.DEPRECATION_BLOCK_AFTER_SUNSET:
                            logger.warning(f"Blocked request to sunset API: {path}")
                            return JSONResponse(
                                status_code=410,
                                content={
                                    "status": "ERROR",
                                    "msg": f"This API version ({matched_pattern}) was sunset on {sunset_str} and is no longer available.",
                                    "errors": ["API Sunsetted"],
                                    "resData": None
                                }
                            )
                            
                    # 2. Pre-Sunset Canary Blocking
                    elif settings.DEPRECATION_CANARY_PERCENT > 0:
                        # Determine client IP or cscId to route canary stability
                        client_ip = request.client.host if request.client else "unknown"
                        # Hash the client identifier to a percentage value [0, 99]
                        hasher = hashlib.md5(client_ip.encode("utf-8"))
                        percent_val = int(hasher.hexdigest(), 16) % 100
                        
                        if percent_val < settings.DEPRECATION_CANARY_PERCENT:
                            logger.warning(f"Canary blocking active for client {client_ip} on deprecated API: {path}")
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "status": "ERROR",
                                    "msg": f"This API version ({matched_pattern}) is deprecated. You have been selected under the canary program (percent: {settings.DEPRECATION_CANARY_PERCENT}%) to migrate to v2 immediately.",
                                    "errors": ["Canary Block active"],
                                    "resData": None
                                }
                            )

            # Process request and add headers
            response = await call_next(request)
            
            # Add sunset headers to indicate deprecation status
            if sunset_str:
                response.headers["Sunset"] = sunset_str
                response.headers["Deprecation"] = "true"
                if settings.DEPRECATION_WARN_BEFORE_SUNSET:
                    response.headers["Warning"] = f'299 - "The API version is deprecated and scheduled for sunset on {sunset_str}. Please migrate immediately."'
                    
            return response
            
        return await call_next(request)
