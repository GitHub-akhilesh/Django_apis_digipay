"""
Ingestion pipeline for the MongoDB RAG store: chunk → embed → upsert.

`seed_knowledge_base()` is idempotent (documents are skipped when their checksum
is unchanged) and safe to call on every application start.
"""

import logging
from typing import Any, Dict, List, Optional

from core.config import settings
from rag.chunker import document_chunker
from rag.knowledge_seed import all_seed_documents
from rag.mongo_store import mongo_vector_store

logger = logging.getLogger("ai_platform.rag.ingest")

# Chunking used for the seed corpus. See seed_knowledge_base for why this is
# finer than the chunker's 200-word default.
SEED_CHUNK_SIZE = 90
SEED_OVERLAP = 20


class IngestService:
    async def ingest_document(
        self,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 200,
        overlap: int = 40,
    ) -> Dict[str, Any]:
        """Chunk, embed and upsert one document."""
        if not source or not source.strip():
            return {"source": source, "indexed": 0, "skipped": True, "reason": "missing source"}
        if not content or not content.strip():
            return {"source": source, "indexed": 0, "skipped": True, "reason": "empty content"}

        chunks = document_chunker.chunk_document(
            content, source, chunk_size=chunk_size, overlap=overlap
        )
        return await mongo_vector_store.upsert_document(
            source=source, content=content, chunks=chunks, metadata=metadata
        )

    async def ingest_many(
        self,
        documents: List[Dict[str, Any]],
        chunk_size: int = 200,
        overlap: int = 40,
    ) -> Dict[str, Any]:
        results = []
        for doc in documents:
            results.append(await self.ingest_document(
                source=doc.get("source", ""),
                content=doc.get("content", ""),
                metadata=doc.get("metadata"),
                chunk_size=chunk_size,
                overlap=overlap,
            ))
        return {
            "documents": len(results),
            "indexedChunks": sum(r.get("indexed", 0) for r in results),
            "skipped": [r for r in results if r.get("skipped")],
            "results": results,
        }

    async def seed_knowledge_base(self, force: bool = False) -> Dict[str, Any]:
        """
        Load the SOP corpus plus the registry-derived capability and boundary
        documents. Called at startup when RAG_AUTO_SEED is on.
        """
        if not settings.RAG_ENABLED:
            return {"seeded": False, "reason": "RAG_ENABLED is false"}

        if not await mongo_vector_store.available():
            logger.warning(
                "Skipping RAG seeding: MongoDB is unreachable. FAQ answers will use the "
                "in-memory index until Mongo is available."
            )
            return {"seeded": False, "reason": "MongoDB unreachable"}

        documents = all_seed_documents()

        if force:
            for doc in documents:
                await mongo_vector_store.delete_document(doc["source"])

        # Seed at a finer granularity than the 200-word default. The SOP documents
        # are short enough that 200 words collapses each into a single chunk, and
        # the generated capability document is long enough that coarse chunks span
        # several unrelated tool domains — both hurt retrieval precision.
        result = await self.ingest_many(documents, chunk_size=SEED_CHUNK_SIZE, overlap=SEED_OVERLAP)
        logger.info(
            f"RAG knowledge base seeded: {result['documents']} documents, "
            f"{result['indexedChunks']} new chunks indexed."
        )
        return {"seeded": True, **result}

    async def remove_document(self, source: str) -> Dict[str, Any]:
        deleted = await mongo_vector_store.delete_document(source)
        return {"source": source, "deletedChunks": deleted}


ingest_service = IngestService()
