from typing import Optional
from core.error_codes import ErrorCode, DEFAULT_USER_MESSAGES
from monitoring.mdc import get_current_trace_id, get_request_id

class AIPlatformException(Exception):
    """
    Base Exception for the AI Platform.
    Binds HTTP status, ErrorCode catalog key, user message, developer diagnostics, traceId, and requestId.
    """
    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode | str,
        user_message: Optional[str] = None,
        developer_message: Optional[str] = None
    ):
        code_str = error_code.value if isinstance(error_code, ErrorCode) else str(error_code)
        self.status_code = status_code
        self.error_code = code_str
        self.user_message = user_message or DEFAULT_USER_MESSAGES.get(error_code, "An error occurred.")
        self.developer_message = developer_message or self.user_message
        self.trace_id = get_current_trace_id() or "unknown"
        self.request_id = get_request_id() or "unknown"
        super().__init__(self.developer_message)

class AuthenticationException(AIPlatformException):
    def __init__(self, developer_message: str = "JWT authentication checks failed"):
        super().__init__(
            status_code=401,
            error_code=ErrorCode.AUTH_INVALID_TOKEN,
            user_message=DEFAULT_USER_MESSAGES[ErrorCode.AUTH_INVALID_TOKEN],
            developer_message=developer_message
        )

class ValidationException(AIPlatformException):
    def __init__(self, developer_message: str):
        super().__init__(
            status_code=400,
            error_code=ErrorCode.VAL_INVALID_PAYLOAD,
            user_message=DEFAULT_USER_MESSAGES[ErrorCode.VAL_INVALID_PAYLOAD],
            developer_message=developer_message
        )

class ToolExecutionException(AIPlatformException):
    def __init__(self, developer_message: str):
        super().__init__(
            status_code=502,
            error_code=ErrorCode.AI_TOOL_EXECUTION_ERROR,
            user_message=DEFAULT_USER_MESSAGES[ErrorCode.AI_TOOL_EXECUTION_ERROR],
            developer_message=developer_message
        )

class LLMException(AIPlatformException):
    def __init__(self, developer_message: str):
        super().__init__(
            status_code=502,
            error_code=ErrorCode.AI_LLM_PROVIDER_ERROR,
            user_message=DEFAULT_USER_MESSAGES[ErrorCode.AI_LLM_PROVIDER_ERROR],
            developer_message=developer_message
        )

class GatewayException(AIPlatformException):
    def __init__(self, developer_message: str):
        super().__init__(
            status_code=504,
            error_code=ErrorCode.GW_TIMEOUT,
            user_message=DEFAULT_USER_MESSAGES[ErrorCode.GW_TIMEOUT],
            developer_message=developer_message
        )
