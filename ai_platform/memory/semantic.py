import logging
from typing import List, Dict, Any

logger = logging.getLogger("ai_platform.memory.semantic")

# In-memory vector semantic store for historical merchant resolutions
HISTORICAL_RESOLUTIONS = [
    {
        "merchantId": "500100100014",
        "query": "settlement IMPS delay payout stuck",
        "resolution": "Resolved by executing manual IMPS bank retry cycle. Merchant received ₹4560.50.",
        "timestamp": "2026-06-15T10:00:00Z"
    },
    {
        "merchantId": "500100100014",
        "query": "Aadhaar Face RD biometric device driver error",
        "resolution": "Guided merchant to install UIDAI Face RD app v2.1 from Play Store.",
        "timestamp": "2026-06-20T14:30:00Z"
    }
]

class SemanticMemoryEngine:
    @staticmethod
    def search_similar_resolutions(query: str, merchant_id: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Search historical resolution memories matching merchant and query semantic keywords."""
        query_words = set(query.lower().split())
        results = []

        for item in HISTORICAL_RESOLUTIONS:
            if merchant_id and item.get("merchantId") != merchant_id:
                continue
                
            item_words = set(item["query"].lower().split())
            intersection = query_words.intersection(item_words)
            if intersection:
                score = len(intersection) / float(len(query_words) or 1)
                results.append({
                    **item,
                    "similarity_score": round(score, 2)
                })

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

semantic_memory_engine = SemanticMemoryEngine()
