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

class PermissionDeniedException(AuthenticationException):
    """
    The caller is authenticated but their role does not permit this tool.

    Subclasses AuthenticationException so existing handlers and tests that catch
    the parent keep working, while letting the response layer distinguish "you are
    not allowed to see this" from "the backend failed" — the first deserves a clear
    explanation, the second an escalation.
    """


class TenantIsolationException(AuthenticationException):
    """The caller tried to read a record belonging to a different CSC ID."""


class UpstreamSessionException(AuthenticationException):
    """
    A downstream service rejected the caller's session (401/403).

    Distinct from a backend fault: the DigiPay gateway keeps server-side session
    state and answers "Session expired" once it lapses, even though the JWT is
    still structurally valid. Reporting that as an outage sends the user to
    human support when all they need to do is sign in again.
    """


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
    def __init__(self, developer_message: str = None, user_message: Optional[str] = None):
        # user_message is optional so a downstream *business* rejection can carry
        # the service's own explanation through to the caller, while transport
        # failures keep the generic catalog wording. Without this the business
        # branch in gateway.base_client raised TypeError instead of an exception
        # the API layer could render.
        super().__init__(
            status_code=504,
            error_code=ErrorCode.GW_TIMEOUT,
            user_message=user_message or DEFAULT_USER_MESSAGES[ErrorCode.GW_TIMEOUT],
            developer_message=developer_message or user_message
        )
