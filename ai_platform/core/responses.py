from typing import Generic, TypeVar, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime, UTC
from fastapi.responses import JSONResponse

from monitoring.mdc import get_current_trace_id, get_request_id
from core.error_codes import ErrorCode, DEFAULT_USER_MESSAGES

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """
    Global DigiPay Standard API Response Wrapper.
    Matches Java ResponseEntity<ApiResponse<T>> output structure.
    """
    success: bool
    data: Optional[T] = None
    errorCode: Optional[str] = None
    message: str
    developerMessage: Optional[str] = None
    traceId: str
    requestId: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    version: str = "v1"

    @classmethod
    def respond_success(
        cls,
        data: Optional[T] = None,
        message: str = "Success",
        status_code: int = 200,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> JSONResponse:
        """Constructs a successful JSON response."""
        payload = cls(
            success=True,
            data=data,
            message=message,
            traceId=get_current_trace_id() or "unknown",
            requestId=get_request_id() or "unknown"
        )
        return JSONResponse(
            status_code=status_code,
            content=payload.model_dump(exclude_none=True),
            headers=extra_headers
        )

    @classmethod
    def respond_error(
        cls,
        error_code: ErrorCode | str,
        message: Optional[str] = None,
        developer_message: Optional[str] = None,
        status_code: int = 400,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> JSONResponse:
        """Constructs an error JSON response."""
        code_str = error_code.value if isinstance(error_code, ErrorCode) else str(error_code)
        user_msg = message or DEFAULT_USER_MESSAGES.get(error_code, "An error occurred.")
        
        payload = cls(
            success=False,
            errorCode=code_str,
            message=user_msg,
            developerMessage=developer_message,
            traceId=get_current_trace_id() or "unknown",
            requestId=get_request_id() or "unknown"
        )
        return JSONResponse(
            status_code=status_code,
            content=payload.model_dump(exclude_none=True),
            headers=extra_headers
        )

    @classmethod
    def success_response(cls, *args, **kwargs):
        return cls.respond_success(*args, **kwargs)

    @classmethod
    def error_response(cls, *args, **kwargs):
        return cls.respond_error(*args, **kwargs)
