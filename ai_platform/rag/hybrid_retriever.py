import logging
import math
from typing import Any, Dict, List

from core.config import settings
from rag.chunker import document_chunker
from rag.mongo_store import mongo_vector_store
from rag.vector_db import vector_db

logger = logging.getLogger("ai_platform.rag.hybrid_retriever")

# Chunk width the keyword score treats as neutral. Chunks wider than this are
# progressively discounted so breadth cannot substitute for relevance.
REFERENCE_CHUNK_WORDS = 120

# Documents that describe the assistant itself rather than DigiPay's rules. They
# are generated from the tool registry and the gateway allow-list, so they are
# long and mention every domain — which makes them lexically competitive on almost
# any query. They should win only when the user is asking about the assistant.
META_CATEGORIES = ("capability", "boundary")
META_SOURCE_HINTS = ("assistant capabilities", "assistant boundaries")

# Markers that the question is about the assistant's own abilities or limits.
SELF_REFERENTIAL_MARKERS = (
    "you", "your", "yourself", "assistant", "bot", "chat",
    "can i ask", "able to", "allowed to", "capabilit", "support",
)

META_BOOST = 1.35
META_PENALTY = 0.55

# Retained in-memory corpus. This is the fallback index used when MongoDB is not
# reachable, and it keeps the synchronous `retrieve()` contract working exactly as
# before for any caller that depends on it.
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
    """
    Hybrid retrieval over the knowledge base.

    `aretrieve` is the preferred entry point: it queries the MongoDB vector store
    and falls back to the in-memory index if Mongo is unavailable. `retrieve`
    remains a synchronous in-memory search so existing callers keep working.

    Both paths apply the same re-ranking: vector similarity, BM25-style keyword
    overlap, and an intent boost.
    """

    def __init__(self):
        # Index the sample SOPs into the in-memory fallback store.
        if not vector_db.chunks:
            for doc in SAMPLE_KNOWLEDGE_DOCS:
                chunks = document_chunker.chunk_document(doc["content"], doc["source"])
                vector_db.add_chunks(chunks)

    # ------------------------------------------------------------------- public

    async def aretrieve(
        self, query: str, intent: str = "FAQ", top_k: int = None
    ) -> List[Dict[str, Any]]:
        """MongoDB-backed retrieval with an in-memory fallback."""
        top_k = top_k or settings.RAG_TOP_K
        logger.info(f"HybridRetriever.aretrieve: query='{query}', intent='{intent}'")

        candidates: List[Dict[str, Any]] = []
        if settings.RAG_ENABLED:
            try:
                candidates = await mongo_vector_store.search(
                    query, top_k=max(top_k * 3, settings.RAG_TOP_K)
                )
            except Exception as e:
                logger.warning(f"MongoDB retrieval failed: {e}. Falling back to in-memory index.")

        if not candidates:
            logger.info("No MongoDB matches; using the in-memory vector index.")
            candidates = vector_db.similarity_search(query, top_k=max(top_k * 3, 5))

        return self._rerank(candidates, query, intent, top_k)

    def retrieve(self, query: str, intent: str = "FAQ", top_k: int = 2) -> List[Dict[str, Any]]:
        """Synchronous in-memory retrieval (unchanged behaviour)."""
        logger.info(f"HybridRetriever.retrieve: query='{query}', intent='{intent}'")
        candidates = vector_db.similarity_search(query, top_k=5)
        return self._rerank(candidates, query, intent, top_k)

    # ------------------------------------------------------------------ ranking

    @staticmethod
    def _rerank(
        candidates: List[Dict[str, Any]], query: str, intent: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Weighted hybrid score: 50% vector + 30% keyword overlap, x intent boost.

        Keyword overlap is length-normalised. Without it a long chunk wins simply
        by containing more vocabulary — which made the generated capability
        document outrank the topic-specific SOPs on almost every query.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        self_referential = any(marker in query_lower for marker in SELF_REFERENTIAL_MARKERS)
        scored_results = []

        for item in candidates:
            text = item.get("text", "")
            source = item.get("source", "")
            text_words = set(text.lower().split())
            overlap = len(query_words.intersection(text_words))
            keyword_match_ratio = overlap / float(len(query_words) or 1)

            # Penalise breadth: a chunk covering many topics is a weaker match for
            # a specific question than a short chunk about exactly that topic.
            # log keeps this a gentle correction rather than a hard cutoff.
            length_penalty = 1.0 + math.log1p(max(len(text_words) - REFERENCE_CHUNK_WORDS, 0) / 100.0)
            keyword_score = keyword_match_ratio / length_penalty

            vec_score = item.get("vector_score", 0.0)
            intent_upper = (intent or "").upper()
            intent_boost = 1.2 if (
                intent_upper and (intent_upper in text.upper() or intent_upper in source.upper())
            ) else 1.0

            is_meta = (
                item.get("category") in META_CATEGORIES
                or any(hint in source.lower() for hint in META_SOURCE_HINTS)
            )
            meta_factor = 1.0
            if is_meta:
                meta_factor = META_BOOST if self_referential else META_PENALTY

            hybrid_score = (0.5 * vec_score + 0.3 * keyword_score) * intent_boost * meta_factor
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
