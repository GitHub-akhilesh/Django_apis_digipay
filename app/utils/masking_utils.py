import re
from typing import Optional

def mask_pii(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'\b\d{8}(\d{4})\b', r'XXXX XXXX \1', text)
    text = re.sub(r'\b(\d{2})\d{6}(\d{2})\b', r'\1XXXXXX\2', text)
    return text


def format_masked_aadhaar(aadhaar: Optional[str]) -> str:
    if not aadhaar:
        return "XXXX XXXX XXXX"
    if "X" in aadhaar or "x" in aadhaar:
        return aadhaar
    clean = aadhaar.replace(" ", "").replace("-", "")
    if len(clean) >= 4:
        last_4 = clean[-4:]
        return f"XXXX XXXX {last_4}"
    return aadhaar
