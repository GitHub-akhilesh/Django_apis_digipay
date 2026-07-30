"""
Governance and knowledge-base administration endpoints.

Exposes what the assistant can reach (the tool catalogue), what it deliberately
cannot (the gateway exclusion register), and control over the MongoDB RAG store.
The two registers are served straight from the code that enforces them, so this
is an audit surface rather than documentation that can drift.
"""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.config import settings
from core.responses import ApiResponse
from gateway.legacy_v1.client import describe_allow_list as describe_legacy_allow_list
from gateway.legacy_v1.client import describe_exclusions as describe_legacy_exclusions
from gateway.v2.safety import describe_allow_list, describe_exclusions
from rag.hybrid_retriever import hybrid_retriever
from rag.ingest import ingest_service
from rag.mongo_store import mongo_vector_store
from tools.catalog import catalog_summary, visible_tools

logger = logging.getLogger("ai_platform.api.routers.knowledge")
router = APIRouter(prefix="/api/v1/governance", tags=["Capability Governance & Knowledge Base"])


class IngestRequest(BaseModel):
    source: str = Field(..., description="Document name, used as the upsert key.")
    content: str = Field(..., description="Raw document text. Lines beginning with # start a section; 'Page N:' sets the page anchor.")
    category: Optional[str] = Field(None, description="Optional classification stored as metadata.")
    chunkSize: int = 200
    overlap: int = 40


class SearchRequest(BaseModel):
    query: str
    topK: int = 4
    source: Optional[str] = None
    rerank: bool = Field(
        True,
        description="True mirrors what chat retrieves (hybrid re-ranking applied). "
                    "False returns raw vector-store order, for tuning the store itself.",
    )


# ---------------------------------------------------------------- capabilities

@router.get("/capabilities")
async def get_capabilities(role: Optional[str] = None):
    """
    Tool catalogue with governance metadata. Pass `role` to see exactly what a
    caller with that role would be offered.
    """
    roles = [role] if role else None
    return ApiResponse.respond_success(
        data={
            "summary": catalog_summary(),
            "tools": [meta.to_dict() for meta in visible_tools(roles=roles)],
        },
        message="Tool catalogue resolved from the live registry.",
    )


@router.get("/gateway/allowed")
async def get_allowed_endpoints():
    """
    Read-only endpoints the assistant is permitted to call, across both backing
    systems: the Spring Boot gateway-service and the legacy DigiPay API service.
    """
    gateway = describe_allow_list()
    legacy = describe_legacy_allow_list()
    return ApiResponse.respond_success(
        data={
            "count": len(gateway) + len(legacy),
            "byService": {"gateway-service": len(gateway), "legacy-digipay-api": len(legacy)},
            "endpoints": gateway + legacy,
        },
        message="Read-only endpoint allow-list.",
    )


@router.get("/gateway/excluded")
async def get_excluded_endpoints():
    """
    Endpoints deliberately withheld from the assistant, with the reason
    (money movement, write, authentication, callback, unsupported transport).
    """
    exclusions = describe_exclusions() + describe_legacy_exclusions()
    by_reason = {}
    for item in exclusions:
        by_reason[item["reason"]] = by_reason.get(item["reason"], 0) + 1
    return ApiResponse.respond_success(
        data={"count": len(exclusions), "byReason": by_reason, "endpoints": exclusions},
        message="Endpoints excluded from the assistant by design.",
    )


@router.get("/services")
async def get_backing_services():
    """
    The systems the assistant reads from and where each is configured to live.
    Useful for confirming a deployment is pointed at the right hosts.
    """
    from tools.registry import TOOL_REGISTRY

    tools_by_source = {}
    for meta in TOOL_REGISTRY.values():
        tools_by_source[meta.source] = tools_by_source.get(meta.source, 0) + 1

    return ApiResponse.respond_success(
        data={
            "services": [
                {
                    "name": "gateway-service",
                    "description": "DigiPay Spring Boot API gateway (/v2/*, /v1/upi/*)",
                    # The resolved URL, with the context path normalised — this is
                    # what calls actually go to, not the raw setting.
                    "baseUrl": settings.gateway_base_url,
                    "configuredUrl": settings.API_GATEWAY_URL,
                    "contextPath": settings.API_GATEWAY_CONTEXT_PATH,
                    "healthPath": settings.API_GATEWAY_HEALTH_PATH,
                    "toolCount": tools_by_source.get("gateway_v2", 0),
                },
                {
                    "name": "legacy-digipay-api",
                    "description": "Legacy DigiPay API service (app/main.py), deployed separately",
                    "baseUrl": settings.LEGACY_API_URL,
                    "pathPrefix": settings.LEGACY_API_PREFIX,
                    "documentedInThisSwagger": settings.AGGREGATE_LEGACY_OPENAPI,
                    "toolCount": tools_by_source.get("legacy_digipay_api", 0),
                },
            ],
            "toolsBySource": tools_by_source,
        },
        message="Backing services the assistant reads from.",
    )


# ------------------------------------------------------------------ RAG store

@router.get("/rag/status")
async def rag_status():
    """MongoDB RAG store health, document counts and embedding configuration."""
    return ApiResponse.respond_success(
        data=await mongo_vector_store.status(),
        message="RAG knowledge store status.",
    )


@router.post("/rag/seed")
async def rag_seed(force: bool = False):
    """
    Load the SOP corpus plus the registry-derived capability and boundary
    documents. Idempotent; pass force=true to re-embed unchanged documents.
    """
    result = await ingest_service.seed_knowledge_base(force=force)
    return ApiResponse.respond_success(data=result, message="RAG knowledge base seeding complete.")


@router.post("/rag/documents")
async def rag_ingest(req: IngestRequest):
    """Ingest or replace a single knowledge document."""
    result = await ingest_service.ingest_document(
        source=req.source,
        content=req.content,
        metadata={"category": req.category} if req.category else None,
        chunk_size=req.chunkSize,
        overlap=req.overlap,
    )
    return ApiResponse.respond_success(data=result, message="Document ingested.")


@router.delete("/rag/documents/{source}")
async def rag_delete(source: str):
    """Remove a document and all of its chunks from the RAG store."""
    result = await ingest_service.remove_document(source)
    return ApiResponse.respond_success(data=result, message="Document removed from the RAG store.")


@router.post("/rag/search")
async def rag_search(req: SearchRequest):
    """Run a retrieval query directly — useful for tuning and for verifying ingestion."""
    if req.rerank and not req.source:
        results = await hybrid_retriever.aretrieve(req.query, intent="FAQ", top_k=req.topK)
        mode = "hybrid (as used by chat)"
    else:
        results = await mongo_vector_store.search(req.query, top_k=req.topK, source=req.source)
        mode = "raw vector store"

    return ApiResponse.respond_success(
        data={"query": req.query, "mode": mode, "matches": len(results), "results": results},
        message="Retrieval executed against the RAG store.",
    )
