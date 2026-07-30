"""
MongoDB-backed vector store for the DigiPay knowledge base.

Collections
-----------
rag_documents   one record per source document (source, title, checksum, meta)
rag_chunks      one record per chunk: text, embedding, source, section, page

Retrieval
---------
Two modes, chosen by MONGO_VECTOR_SEARCH_ENABLED:

  $vectorSearch   MongoDB Atlas Vector Search — the index does the work.
  in-process      candidates are narrowed with a Mongo text/regex filter, then
                  cosine similarity is computed here. Works on any standalone
                  MongoDB with no Atlas dependency.

Availability
------------
Mongo is treated as an enhancement, never a hard dependency: if the driver is
missing or the server is unreachable, `available()` reports False and callers
fall back to the in-memory index. Chat degrades in retrieval quality, not in
uptime.
"""

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional

from core.config import settings
from rag.embeddings import cosine_similarity, get_embedder

logger = logging.getLogger("ai_platform.rag.mongo_store")


class MongoVectorStore:
    def __init__(self):
        self._client = None
        self._db = None
        self._checked = False
        self._available = False
        self._indexes_ready = False
        self._loop = None

    # ------------------------------------------------------------- connection

    def _reset(self):
        """Drop the cached client so the next call reconnects."""
        self._client = None
        self._db = None
        self._checked = False
        self._available = False
        self._indexes_ready = False
        self._loop = None

    def _connect(self):
        """Create the Motor client. Never raises — sets _available instead."""
        if self._checked:
            return
        self._checked = True

        if not settings.RAG_ENABLED:
            logger.info("RAG is disabled by configuration (RAG_ENABLED=false).")
            return

        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError:
            logger.warning(
                "motor is not installed — MongoDB RAG is inactive and retrieval will use "
                "the in-memory index. Install with: pip install motor"
            )
            return

        try:
            self._client = AsyncIOMotorClient(
                settings.MONGO_URI,
                connectTimeoutMS=settings.MONGO_CONNECT_TIMEOUT_MS,
                serverSelectionTimeoutMS=settings.MONGO_SERVER_SELECTION_TIMEOUT_MS,
            )
            self._db = self._client[settings.MONGO_DB]
            self._available = True
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
            logger.info(f"MongoDB RAG store configured: db='{settings.MONGO_DB}'")
        except Exception as e:
            logger.warning(f"MongoDB RAG store could not be configured: {e}")
            self._available = False

    async def available(self) -> bool:
        """True when the server actually answers a ping."""
        # A Motor client is bound to the event loop it was created on. Recreate it
        # if the loop has changed, which happens when the process runs more than
        # one asyncio.run (workers, scripts, per-test loops).
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if self._client is not None and self._loop is not None and self._loop is not current_loop:
            logger.debug("Event loop changed; reconnecting the MongoDB RAG client.")
            self._client.close()
            self._reset()

        self._connect()
        if not self._available or self._client is None:
            return False
        try:
            await self._client.admin.command("ping")
            return True
        except Exception as e:
            logger.warning(f"MongoDB RAG store unreachable: {e}")
            return False

    @property
    def chunks(self):
        self._connect()
        if self._db is None:
            return None
        return self._db[settings.MONGO_RAG_CHUNKS_COLLECTION]

    @property
    def documents(self):
        self._connect()
        if self._db is None:
            return None
        return self._db[settings.MONGO_RAG_DOCS_COLLECTION]

    async def ensure_indexes(self):
        """Create the supporting indexes once per process."""
        if self._indexes_ready or self.chunks is None:
            return
        try:
            await self.chunks.create_index("chunk_id", unique=True)
            await self.chunks.create_index("source")
            await self.chunks.create_index([("text", "text"), ("section", "text")])
            await self.documents.create_index("source", unique=True)
            self._indexes_ready = True
            logger.info("MongoDB RAG indexes ensured.")
        except Exception as e:
            # A duplicate/conflicting text index is not fatal — retrieval still works.
            logger.warning(f"Could not ensure MongoDB RAG indexes: {e}")
            self._indexes_ready = True

    # ---------------------------------------------------------------- ingestion

    @staticmethod
    def _checksum(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def upsert_document(
        self,
        source: str,
        content: str,
        chunks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Replace a document's chunks with a freshly embedded set.

        Skipped when the content checksum is unchanged, so repeated startup
        seeding does not re-embed identical documents.
        """
        if not await self.available():
            return {"source": source, "indexed": 0, "skipped": True, "reason": "store unavailable"}

        await self.ensure_indexes()
        checksum = self._checksum(content)

        existing = await self.documents.find_one({"source": source})
        if existing and existing.get("checksum") == checksum:
            return {"source": source, "indexed": 0, "skipped": True, "reason": "unchanged"}

        embedder = get_embedder()
        texts = [c["text"] for c in chunks]
        vectors = embedder.embed_batch(texts) if texts else []

        category = (metadata or {}).get("category", "general")
        docs = []
        for chunk, vector in zip(chunks, vectors):
            docs.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "source": chunk["source"],
                "section": chunk.get("section", "General"),
                "page": chunk.get("page", 1),
                # Carried onto the chunk so the re-ranker can tell knowledge about
                # DigiPay apart from knowledge about the assistant itself.
                "category": category,
                "embedding": vector,
                "embedding_provider": embedder.provider_name,
                "embedding_dim": len(vector),
            })

        try:
            await self.chunks.delete_many({"source": source})
            if docs:
                await self.chunks.insert_many(docs)
            await self.documents.update_one(
                {"source": source},
                {"$set": {
                    "source": source,
                    "checksum": checksum,
                    "chunkCount": len(docs),
                    "metadata": metadata or {},
                    "embeddingProvider": embedder.provider_name,
                }},
                upsert=True,
            )
            logger.info(f"Indexed {len(docs)} chunks for '{source}' into MongoDB.")
            return {"source": source, "indexed": len(docs), "skipped": False}
        except Exception as e:
            logger.error(f"Failed to index '{source}' into MongoDB: {e}")
            return {"source": source, "indexed": 0, "skipped": True, "reason": str(e)}

    async def delete_document(self, source: str) -> int:
        if not await self.available():
            return 0
        result = await self.chunks.delete_many({"source": source})
        await self.documents.delete_one({"source": source})
        return result.deleted_count

    # ---------------------------------------------------------------- retrieval

    async def search(
        self, query: str, top_k: Optional[int] = None, source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Similarity search. Returns [] when the store is unavailable or empty."""
        if not await self.available():
            return []

        top_k = top_k or settings.RAG_TOP_K
        embedder = get_embedder()
        query_vector = embedder.embed(query)

        if settings.MONGO_VECTOR_SEARCH_ENABLED:
            results = await self._atlas_search(query_vector, top_k, source)
            if results:
                return results
            logger.warning(
                "$vectorSearch returned nothing; falling back to in-process scoring. "
                "Check that the Atlas index name matches MONGO_VECTOR_INDEX."
            )

        return await self._in_process_search(query, query_vector, top_k, source)

    async def _atlas_search(
        self, query_vector: List[float], top_k: int, source: Optional[str]
    ) -> List[Dict[str, Any]]:
        pipeline: List[Dict[str, Any]] = [{
            "$vectorSearch": {
                "index": settings.MONGO_VECTOR_INDEX,
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": settings.RAG_CANDIDATE_POOL,
                "limit": top_k,
            }
        }]
        if source:
            pipeline.append({"$match": {"source": source}})
        pipeline.append({
            "$project": {
                "_id": 0, "chunk_id": 1, "text": 1, "source": 1, "section": 1,
                "page": 1, "category": 1, "vector_score": {"$meta": "vectorSearchScore"},
            }
        })

        try:
            return [doc async for doc in self.chunks.aggregate(pipeline)]
        except Exception as e:
            logger.warning(f"Atlas $vectorSearch failed: {e}")
            return []

    async def _in_process_search(
        self, query: str, query_vector: List[float], top_k: int, source: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Narrow with a Mongo text search when it yields hits, otherwise score the
        whole (bounded) candidate pool. Cosine similarity is computed here.
        """
        base_filter: Dict[str, Any] = {"source": source} if source else {}
        projection = {"_id": 0, "chunk_id": 1, "text": 1, "source": 1,
                      "section": 1, "page": 1, "category": 1, "embedding": 1}
        pool = settings.RAG_CANDIDATE_POOL

        candidates: List[Dict[str, Any]] = []
        try:
            text_filter = {**base_filter, "$text": {"$search": query}}
            cursor = self.chunks.find(text_filter, projection).limit(pool)
            candidates = [doc async for doc in cursor]
        except Exception as e:
            logger.debug(f"Mongo text search unavailable ({e}); scoring the full pool.")

        if not candidates:
            try:
                cursor = self.chunks.find(base_filter, projection).limit(pool)
                candidates = [doc async for doc in cursor]
            except Exception as e:
                logger.warning(f"Mongo candidate fetch failed: {e}")
                return []

        scored = []
        for doc in candidates:
            score = cosine_similarity(query_vector, doc.get("embedding") or [])
            if score < settings.RAG_MIN_SCORE:
                continue
            scored.append({
                "chunk_id": doc.get("chunk_id"),
                "text": doc.get("text", ""),
                "source": doc.get("source", "Knowledge Base"),
                "section": doc.get("section", "General"),
                "page": doc.get("page", 1),
                "category": doc.get("category", "general"),
                "vector_score": round(score, 4),
            })

        scored.sort(key=lambda x: x["vector_score"], reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------- status

    async def status(self) -> Dict[str, Any]:
        from rag.embeddings import embedding_info

        reachable = await self.available()
        info: Dict[str, Any] = {
            "ragEnabled": settings.RAG_ENABLED,
            "mongoReachable": reachable,
            "database": settings.MONGO_DB,
            "vectorSearchEnabled": settings.MONGO_VECTOR_SEARCH_ENABLED,
            "vectorIndex": settings.MONGO_VECTOR_INDEX,
            "embedding": embedding_info(),
            "documents": 0,
            "chunks": 0,
            "sources": [],
        }
        if not reachable:
            info["fallback"] = "in-memory vector index (rag.vector_db)"
            return info

        try:
            info["documents"] = await self.documents.count_documents({})
            info["chunks"] = await self.chunks.count_documents({})
            info["sources"] = await self.documents.distinct("source")
        except Exception as e:
            logger.warning(f"Could not read MongoDB RAG stats: {e}")
        return info

    async def close(self):
        if self._client is not None:
            self._client.close()
        self._reset()


mongo_vector_store = MongoVectorStore()
