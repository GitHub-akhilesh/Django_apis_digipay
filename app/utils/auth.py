import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from app.config import settings

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.JWT_EXPIRY_SECONDS)
    
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def decode_jwt_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def is_internal_bypass(request: Request) -> bool:
    if not settings.ENABLE_INTERNAL_AUTH_BYPASS:
        return False
        
    client_id = request.headers.get("X-Client-Id")
    bypass_secret = request.headers.get("X-Bypass-Secret")
    
    if not client_id or not bypass_secret:
        return False
        
    # Check if client_id is in permitted internal clients and secret matches
    if client_id in settings.internal_clients_set and bypass_secret == settings.INTERNAL_BYPASS_SECRET:
        return True
        
    return False
