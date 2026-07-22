import re
from typing import Tuple, Dict

AADHAAR_REGEX = r"\b\d{12}\b"
PAN_REGEX = r"\b[A-Z]{5}\d{4}[A-Z]\b"
MOBILE_REGEX = r"\b[6-9]\d{9}\b"
EMAIL_REGEX = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"

class PIIInputFilter:
    @staticmethod
    def mask_pii(text: str) -> Tuple[str, Dict[str, str]]:
        """Mask PII fields and return masked text along with restore map."""
        restore_map = {}
        masked_text = text

        # 1. Email Masking
        emails = re.findall(EMAIL_REGEX, masked_text)
        for idx, email in enumerate(emails):
            key = f"[EMAIL_MASK_{idx}]"
            restore_map[key] = email
            masked_text = masked_text.replace(email, key)

        # 2. PAN Masking
        pans = re.findall(PAN_REGEX, masked_text)
        for idx, pan in enumerate(pans):
            key = f"[PAN_MASK_{idx}]"
            restore_map[key] = pan
            masked_text = masked_text.replace(pan, key)

        # 3. Aadhaar Masking
        aadhaars = re.findall(AADHAAR_REGEX, masked_text)
        for idx, aadhaar in enumerate(aadhaars):
            key = f"[AADHAAR_MASK_{idx}]"
            restore_map[key] = aadhaar
            masked_text = masked_text.replace(aadhaar, key)

        # 4. Mobile Masking
        mobiles = re.findall(MOBILE_REGEX, masked_text)
        for idx, mobile in enumerate(mobiles):
            key = f"[MOBILE_MASK_{idx}]"
            restore_map[key] = mobile
            masked_text = masked_text.replace(mobile, key)

        return masked_text, restore_map

    @staticmethod
    def restore_pii(text: str, restore_map: Dict[str, str]) -> str:
        """Restore original PII values back into the text using restore map."""
        restored_text = text
        for key, val in restore_map.items():
            restored_text = restored_text.replace(key, val)
        return restored_text

pii_input_filter = PIIInputFilter()
