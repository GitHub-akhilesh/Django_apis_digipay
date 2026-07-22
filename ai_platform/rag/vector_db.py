import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ai_platform.rag.vector_db")

class VectorDBStore:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []

    def _get_embedding(self, text: str) -> List[float]:
        """Simulate vector embedding generation (normalized word frequencies)."""
        words = text.lower().split()
        vocab = ["wallet", "balance", "settlement", "imps", "neft", "chargeback", "npci", "biometric", "face", "rd", "aadhaar", "driver", "kyc"]
        vec = [words.count(w) for w in vocab]
        norm = math.sqrt(sum(x*x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Add chunks to the vector database index."""
        for c in chunks:
            c["vector"] = self._get_embedding(c["text"])
            self.chunks.append(c)

    def similarity_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Perform cosine similarity search against indexed vector chunks."""
        q_vec = self._get_embedding(query)
        results = []

        for chunk in self.chunks:
            c_vec = chunk["vector"]
            cosine_sim = sum(a * b for a, b in zip(q_vec, c_vec))
            if cosine_sim > 0.0:
                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "section": chunk["section"],
                    "page": chunk.get("page", 1),
                    "vector_score": round(cosine_sim, 4)
                })

        results.sort(key=lambda x: x["vector_score"], reverse=True)
        return results[:top_k]

vector_db = VectorDBStore()
