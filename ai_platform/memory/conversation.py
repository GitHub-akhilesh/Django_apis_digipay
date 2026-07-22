from typing import List, Dict, Any, Optional
from memory.summary import summary_memory
from memory.session import session_metadata_memory

class ConversationMemory:
    @staticmethod
    def get_summary(session_id: str) -> Optional[str]:
        return summary_memory.get_summary(session_id)

    @staticmethod
    def save_summary(session_id: str, summary: str):
        summary_memory.save_summary(session_id, summary)

    @staticmethod
    def get_metadata(session_id: str) -> Dict[str, Any]:
        return session_metadata_memory.get_metadata(session_id)

    @staticmethod
    def save_metadata(session_id: str, metadata: Dict[str, Any]):
        session_metadata_memory.save_metadata(session_id, metadata)
