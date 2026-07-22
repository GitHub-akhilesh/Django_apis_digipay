from enum import Enum

class ErrorCode(str, Enum):
    """
    Standardized DigiPay Enterprise Error Catalog Codes.
    Grouped by system boundaries to match microservice standards.
    """
    # ==========================================
    # 1. AUTHENTICATION & AUTHORIZATION (AUTH)
    # ==========================================
    AUTH_MISSING_TOKEN = "AUTH-1001"
    AUTH_INVALID_TOKEN = "AUTH-1002"
    AUTH_ACCESS_DENIED = "AUTH-1003"

    # ==========================================
    # 2. REQUEST VALIDATION (VAL)
    # ==========================================
    VAL_INVALID_PAYLOAD = "VAL-1001"
    VAL_MISSING_HEADER = "VAL-1002"
    VAL_PAYLOAD_TOO_LARGE = "VAL-1003"

    # ==========================================
    # 3. DOWNSTREAM API GATEWAY (GW)
    # ==========================================
    GW_TIMEOUT = "GW-1001"
    GW_SERVICE_UNAVAILABLE = "GW-1002"
    GW_BAD_GATEWAY = "GW-1003"

    # ==========================================
    # 4. AI PLATFORM CORE ENGINE (AI)
    # ==========================================
    AI_GENERAL_ERROR = "AI-1001"
    AI_CONFIG_ERROR = "AI-1002"
    AI_LLM_PROVIDER_ERROR = "AI-1003"
    AI_TOOL_EXECUTION_ERROR = "AI-2001"
    AI_CONTEXT_ERROR = "AI-2002"

# Map error codes to default user-friendly messages
DEFAULT_USER_MESSAGES = {
    ErrorCode.AUTH_MISSING_TOKEN: "Authentication failed. Bearer token is missing.",
    ErrorCode.AUTH_INVALID_TOKEN: "Authentication failed. Invalid token signature or expired.",
    ErrorCode.AUTH_ACCESS_DENIED: "Access denied. Insufficient permissions for this resource.",
    ErrorCode.VAL_INVALID_PAYLOAD: "Input payload fails schema validation.",
    ErrorCode.VAL_MISSING_HEADER: "Required request header is missing.",
    ErrorCode.VAL_PAYLOAD_TOO_LARGE: "Message size exceeds maximum allowable limit.",
    ErrorCode.GW_TIMEOUT: "Downstream backend gateway timed out.",
    ErrorCode.GW_SERVICE_UNAVAILABLE: "Downstream microservice is temporarily unavailable.",
    ErrorCode.GW_BAD_GATEWAY: "Invalid response received from downstream gateway service.",
    ErrorCode.AI_GENERAL_ERROR: "An internal platform error occurred.",
    ErrorCode.AI_CONFIG_ERROR: "Platform configuration error.",
    ErrorCode.AI_LLM_PROVIDER_ERROR: "Failed to communicate with LLM engine.",
    ErrorCode.AI_TOOL_EXECUTION_ERROR: "Tool execution failed during operation.",
    ErrorCode.AI_CONTEXT_ERROR: "Failed to resolve conversation context memory."
}
