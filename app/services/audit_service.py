import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("digipay_audit")

class AuditService:
    """Structured security and operational audit logging service."""

    @staticmethod
    def log_access(merchant_id: str, action: str, details: Optional[Dict[str, Any]] = None):
        logger.info(f"AUDIT_ACCESS | merchant_id={merchant_id} | action={action} | details={details or {}}")

    @staticmethod
    def log_tool_execution(merchant_id: str, tool_name: str, args: Dict[str, Any], status: str):
        logger.info(f"AUDIT_TOOL | merchant_id={merchant_id} | tool={tool_name} | status={status} | args={args}")

    @staticmethod
    def log_security_event(merchant_id: str, event_type: str, message: str):
        logger.warning(f"AUDIT_SECURITY_ALERT | merchant_id={merchant_id} | event={event_type} | message={message}")
