"""
Embedding generation for the RAG store.

Two providers:

  openai   real embeddings via the OpenAI embeddings API, used when
           OPENAI_API_KEY is configured and the SDK is installed.
  hashing   a deterministic, dependency-free feature-hashing embedder used
            otherwise. It hashes word unigrams and bigrams into a fixed-width
            vector and L2-normalises the result, so cosine similarity behaves
            sensibly for keyword-overlapping text.

The hashing provider exists so the knowledge base is queryable in local and
CI environments with no API key and no model download. It is a genuine
lexical-similarity embedder, not a semantic one — swap RAG_EMBEDDING_PROVIDER
to `openai` (or point it at your own service) for semantic retrieval in
production.
"""

import hashlib
import logging
import math
import re
from typing import List, Optional

from core.config import settings

logger = logging.getLogger("ai_platform.rag.embeddings")

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class HashingEmbedder:
    provider_name = "hashing"

    def __init__(self, dim: int):
        self.dim = dim

    def _tokens(self, text: str) -> List[str]:
        words = TOKEN_PATTERN.findall((text or "").lower())
        bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
        return words + bigrams

    def _bucket(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dim

    def embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dim
        tokens = self._tokens(text)
        if not tokens:
            return vector
        for token in tokens:
            # Sub-linear term weighting keeps a repeated word from dominating.
            vector[self._bucket(token)] += 1.0
        vector = [math.log1p(v) for v in vector]
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class OpenAIEmbedder:
    provider_name = "openai"

    def __init__(self, model: str, dim: int, api_key: str):
        self.model = model
        self.dim = dim
        self.api_key = api_key
        self._client = None
        self._fallback = HashingEmbedder(dim)

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # imported lazily: optional dependency
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self.model, input=texts, dimensions=self.dim
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(
                f"OpenAI embedding failed ({e}). Falling back to the hashing embedder "
                "for this batch — retrieval quality will be lexical, not semantic."
            )
            return self._fallback.embed_batch(texts)


_embedder = None


def get_embedder():
    """Singleton embedder chosen from configuration."""
    global _embedder
    if _embedder is not None:
        return _embedder

    dim = settings.RAG_EMBEDDING_DIM
    provider = (settings.RAG_EMBEDDING_PROVIDER or "auto").lower()
    key = settings.OPENAI_API_KEY or ""

    use_openai = provider == "openai" or (provider == "auto" and key.startswith("sk-"))
    if use_openai and key.startswith("sk-"):
        logger.info(f"RAG embeddings: OpenAI '{settings.RAG_EMBEDDING_MODEL}' (dim={dim})")
        _embedder = OpenAIEmbedder(settings.RAG_EMBEDDING_MODEL, dim, key)
    else:
        if use_openai:
            logger.warning(
                "RAG_EMBEDDING_PROVIDER=openai but no valid OPENAI_API_KEY is set. "
                "Using the hashing embedder instead."
            )
        logger.info(f"RAG embeddings: deterministic hashing embedder (dim={dim})")
        _embedder = HashingEmbedder(dim)

    return _embedder


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity that tolerates a length mismatch between stored vectors."""
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(length))
    norm_a = math.sqrt(sum(x * x for x in a[:length]))
    norm_b = math.sqrt(sum(x * x for x in b[:length]))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def embedding_info() -> dict:
    embedder = get_embedder()
    return {
        "provider": embedder.provider_name,
        "dimensions": embedder.dim,
        "model": getattr(embedder, "model", None),
    }
