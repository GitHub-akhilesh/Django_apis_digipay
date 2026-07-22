import logging
from typing import Dict, Any, Optional
from memory.session import session_metadata_memory

logger = logging.getLogger("ai_platform.memory.context")

class ContextMemory:
    @staticmethod
    def get_merchant_id(session_id: str) -> Optional[str]:
        metadata = session_metadata_memory.get_metadata(session_id)
        return metadata.get("merchant_id")

    @staticmethod
    def set_merchant_id(session_id: str, merchant_id: str):
        metadata = session_metadata_memory.get_metadata(session_id)
        metadata["merchant_id"] = merchant_id
        session_metadata_memory.save_metadata(session_id, metadata)

context_memory = ContextMemory()
