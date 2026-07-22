import re
import unicodedata
from core.exceptions import ValidationException
from core.config import settings

def sanitize_message_input(message: str) -> str:
    """
    Sanitizes chat input string:
    1. Removesnull bytes and non-printable control characters.
    2. Performs Unicode normalization (NFKC).
    3. Compresses repeated whitespaces.
    4. Enforces word count limits.
    """
    if not message or not message.strip():
        raise ValidationException("Chat message input cannot be empty.")
        
    # Standard Unicode Normalization
    normalized = unicodedata.normalize("NFKC", message)

    max_len = getattr(settings, "MAX_MESSAGE_LENGTH", 5000)
    if len(normalized) > max_len:
        raise ValidationException(f"Message length exceeds maximum allowable limit of {max_len} characters.")

    # Remove null bytes or non-printable ASCII/Unicode controls
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", normalized)
    
    # Compress repeated whitespaces
    compressed = re.sub(r"\s+", " ", cleaned).strip()

    # Enforce maximum word count (e.g. 1000 words maximum)
    words = compressed.split(" ")
    if len(words) > 1000:
        raise ValidationException("Message exceeds the maximum limit of 1000 words.")

    return compressed
