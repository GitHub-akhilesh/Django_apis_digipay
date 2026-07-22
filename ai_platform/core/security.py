import hashlib

def secure_sha256(data: str) -> str:
    """Utility to generate secure SHA256 checksum tags."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
