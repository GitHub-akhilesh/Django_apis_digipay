from typing import Any
from core.exceptions import ValidationException
from core.constants import HEADER_B3_TRACE_ID

def validate_mandatory_headers(headers: Any) -> bool:
    """
    Validates presence of required microservice headers.
    """
    # Header names in Starlette headers are case-insensitive
    auth = headers.get("Authorization") or headers.get("authorization")
    if not auth:
        raise ValidationException("Missing mandatory Authorization header.")
    return True
