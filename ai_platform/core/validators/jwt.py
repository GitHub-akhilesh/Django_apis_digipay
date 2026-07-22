from core.exceptions import AuthenticationException

def validate_jwt_format(token: str) -> str:
    """
    Validates structure of raw JWT string:
    1. Rejects excessively large tokens (> 4KB).
    2. Rejects empty segments.
    3. Rejects non-ASCII characters.
    """
    if not token or not isinstance(token, str):
        raise AuthenticationException("Authorization token is missing or malformed.")

    cleaned_token = token.replace("Bearer ", "").strip()
    
    # 1. Enforce length threshold (4KB maximum)
    if len(cleaned_token) > 4096:
        raise AuthenticationException("Token exceeds the maximum size limit of 4KB.")

    # 2. Reject non-ASCII characters
    if not cleaned_token.isascii():
        raise AuthenticationException("Token contains invalid non-ASCII characters.")

    # 3. Verify segments structure
    parts = cleaned_token.split(".")
    if len(parts) != 3:
        raise AuthenticationException("JWT structure is invalid. Must contain header, payload, and signature segments.")

    # 4. Reject empty segments
    for part in parts:
        if not part:
            raise AuthenticationException("JWT contains empty segment elements.")

    return cleaned_token
