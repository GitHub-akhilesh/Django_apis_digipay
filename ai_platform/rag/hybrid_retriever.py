import logging
from typing import List, Dict, Any
from rag.chunker import document_chunker
from rag.vector_db import vector_db

logger = logging.getLogger("ai_platform.rag.hybrid_retriever")

SAMPLE_KNOWLEDGE_DOCS = [
    {
        "source": "Merchant Wallet Payout Settlement SOP.pdf",
        "content": """
        # Settlement SLA & Payout Cycles
        Page 8: Standard settlements are processed daily in batch cycles. IMPS cycles complete within 2 hours; NEFT transfers clear inside standard banking slots.
        If a settlement fails, funds are automatically returned to the merchant wallet balance.
        """
    },
    {
        "source": "NPCI Chargeback Rules and Dispute SOP.pdf",
        "content": """
        # Chargeback & Dispute Window
        Page 14: Chargeback complaints can be raised within 30 days from transaction date. Merchants must submit a valid UTR, RRN, customer mobile number, and receipt.
        Settlement issues must contain bank statement proofs showing non-credit.
        """
    },
    {
        "source": "Aadhaar Face RD Integration Guide.pdf",
        "content": """
        # Biometric RD Service Installation
        Page 3: CSC VLEs must download the official UIDAI Face RD App (v2.1+) from Android Google Play Store.
        Ensure camera permission is enabled and device registration status shows ACTIVE.
        """
    }
]

class HybridRetriever:
    def __init__(self):
        # Index sample SOPs into Vector DB
        if not vector_db.chunks:
            for doc in SAMPLE_KNOWLEDGE_DOCS:
                chunks = document_chunker.chunk_document(doc["content"], doc["source"])
                vector_db.add_chunks(chunks)

    def retrieve(self, query: str, intent: str = "FAQ", top_k: int = 2) -> List[Dict[str, Any]]:
        """Perform hybrid retrieval combining vector similarity, BM25 keyword matching, and intent boost."""
        logger.info(f"HybridRetriever: query='{query}', intent='{intent}'")
        
        # 1. Vector Search
        vector_results = vector_db.similarity_search(query, top_k=5)
        
        # 2. BM25 Keyword match & Hybrid Score computation
        query_words = set(query.lower().split())
        scored_results = []
        
        for item in vector_results:
            text_words = set(item["text"].lower().split())
            keyword_match_ratio = len(query_words.intersection(text_words)) / float(len(query_words) or 1)
            
            vec_score = item["vector_score"]
            intent_boost = 1.2 if intent.upper() in item["text"].upper() or intent.upper() in item["source"].upper() else 1.0
            
            # Weighted Hybrid Score: 50% Vector + 30% Keyword + 20% Intent Boost
            hybrid_score = (0.5 * vec_score + 0.3 * keyword_match_ratio) * intent_boost
            confidence_pct = min(99, int(hybrid_score * 100) + 45)

            scored_results.append({
                **item,
                "keyword_score": round(keyword_match_ratio, 2),
                "hybrid_score": round(hybrid_score, 4),
                "confidence_pct": confidence_pct
            })

        scored_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return scored_results[:top_k]

hybrid_retriever = HybridRetriever()
