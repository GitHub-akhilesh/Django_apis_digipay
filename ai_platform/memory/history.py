import logging
from typing import List, Dict
from memory.redis_memory import session_memory

logger = logging.getLogger("ai_platform.memory.history")

class HistoryMemory:
    @staticmethod
    def get_history(session_id: str) -> List[Dict[str, str]]:
        return session_memory.get_history(session_id)

    @staticmethod
    def save_history(session_id: str, messages: List[Dict[str, str]]):
        session_memory.save_history(session_id, messages)

history_memory = HistoryMemory()
