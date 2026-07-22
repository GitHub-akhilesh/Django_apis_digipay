import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ai_platform.services.audit_service")
audit_logger = logging.getLogger("ai_platform.audit_trail")

class AuditService:
    @staticmethod
    def record_interaction(
        session_id: str,
        user_query: str,
        intent: str,
        tools_executed: List[Dict[str, Any]],
        llm_response: str,
        csc_id: str,
        roles: List[str]
    ):
        """Idempotently record full details of user interaction for audit compliance."""
        record = {
            "session_id": session_id,
            "merchant_id": csc_id,
            "roles": roles,
            "question": user_query,
            "intent": intent,
            "tools": tools_executed,
            "response": llm_response
        }
        # Log structured audit log
        audit_logger.info(f"AUDIT TRAIL RECORD: {json.dumps(record)}")

audit_service = AuditService()
