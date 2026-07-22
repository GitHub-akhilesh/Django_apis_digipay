import time
import logging
from typing import Dict, Any, Optional
from memory.session import session_metadata_memory

logger = logging.getLogger("ai_platform.memory.ranking")

INTENT_IMPORTANCE_SCORES = {
    "REVERSAL": 9.5,
    "REFUND": 9.0,
    "SETTLEMENT": 8.0,
    "WALLET": 7.5,
    "MERCHANT": 6.0,
    "KYC": 5.5,
    "FAQ": 3.0,
    "GENERAL": 2.0
}

class MemoryRankingManager:
    @staticmethod
    def calculate_importance(intent: str) -> float:
        """Calculate conversation importance score based on business severity."""
        return INTENT_IMPORTANCE_SCORES.get(intent.upper(), 4.0)

    @staticmethod
    def calculate_ttl(importance: float) -> int:
        """Calculate TTL (in seconds) based on importance score."""
        if importance >= 8.0:
            return 7 * 86400  # 7 days
        elif importance >= 5.0:
            return 3 * 86400  # 3 days
        return 1 * 86400      # 24 hours

    def record_session_lifecycle(
        self,
        session_id: str,
        intent: str,
        tool_name: Optional[str],
        merchant_id: str,
        user_id: str,
        tokens_used: int,
        summary: str = ""
    ) -> Dict[str, Any]:
        """Record lifecycle metrics into session metadata."""
        importance = self.calculate_importance(intent)
        ttl = self.calculate_ttl(importance)
        expires_at = time.time() + ttl

        current_meta = session_metadata_memory.get_metadata(session_id)
        
        updated_meta = {
            **current_meta,
            "importance": importance,
            "ttl": ttl,
            "expiresAt": expires_at,
            "lastIntent": intent,
            "lastTool": tool_name,
            "merchantId": merchant_id,
            "userId": user_id,
            "conversationTokens": current_meta.get("conversationTokens", 0) + tokens_used,
            "summary": summary or current_meta.get("summary", "")
        }

        session_metadata_memory.save_metadata(session_id, updated_meta)
        logger.info(f"Updated memory lifecycle for session {session_id}: Importance={importance}, TTL={ttl}s")
        return updated_meta

memory_ranking_manager = MemoryRankingManager()
