"""
Tests for the MongoDB-backed RAG knowledge store.

The ingest/search tests run against a real MongoDB when one is reachable and are
skipped otherwise. The degradation tests always run — they are the important
guarantee: chat must keep answering FAQ questions when Mongo is down.
"""

import pytest

from rag.embeddings import HashingEmbedder, cosine_similarity, embedding_info, get_embedder
from rag.hybrid_retriever import hybrid_retriever
from rag.ingest import ingest_service
from rag.knowledge_seed import (
    SOP_DOCUMENTS,
    all_seed_documents,
    build_boundary_document,
    build_capability_document,
)
from rag.mongo_store import mongo_vector_store


# --------------------------------------------------------------------------- #
# Embeddings
# --------------------------------------------------------------------------- #

def test_hashing_embedder_is_deterministic_and_normalised():
    embedder = HashingEmbedder(dim=128)
    a = embedder.embed("settlement IMPS payout delay")
    b = embedder.embed("settlement IMPS payout delay")

    assert a == b
    assert len(a) == 128
    assert cosine_similarity(a, b) == pytest.approx(1.0, abs=1e-9)


def test_hashing_embedder_separates_unrelated_text():
    embedder = HashingEmbedder(dim=256)
    settlement = embedder.embed("settlement payout IMPS NEFT cycle clearing")
    biometric = embedder.embed("fingerprint scanner OTG registration camera")
    related = embedder.embed("payout settlement cycle")

    assert cosine_similarity(settlement, related) > cosine_similarity(settlement, biometric)


def test_empty_text_embeds_without_error():
    embedder = HashingEmbedder(dim=32)
    assert embedder.embed("") == [0.0] * 32
    assert cosine_similarity(embedder.embed(""), embedder.embed("anything")) == 0.0


def test_cosine_tolerates_dimension_mismatch():
    """A stored vector from a differently configured embedder must not crash search."""
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_embedding_info_reports_the_active_provider():
    info = embedding_info()
    assert info["provider"] in ("hashing", "openai")
    assert info["dimensions"] > 0


# --------------------------------------------------------------------------- #
# Seed corpus
# --------------------------------------------------------------------------- #

def test_capability_document_is_generated_from_the_live_registry():
    doc = build_capability_document()
    assert doc["metadata"]["generated"] is True
    # Tools registered from the gateway integration must appear.
    assert "getTxnLogs" in doc["content"]
    assert "getLedgerBalanceV2" in doc["content"]
    assert "read" in doc["content"].lower()


def test_boundary_document_explains_the_read_only_limits():
    doc = build_boundary_document()
    content = doc["content"]
    assert "Money Movement" in content
    assert "Auth" in content
    # Named actions the assistant refuses.
    assert "Wallet-to-wallet fund transfer" in content
    assert "Generates a login OTP" in content


def test_capability_document_is_not_indexed_for_retrieval():
    """
    "What can you do?" is answered from the live registry, so indexing the
    capability sheet adds no reach — and because it is long and names every
    domain, it crowded out the topic-specific SOPs. Regression guard for that.
    """
    sources = [d["source"] for d in all_seed_documents()]
    assert "DigiPay Assistant Capabilities.md" not in sources
    assert "DigiPay Assistant Boundaries.md" in sources


def test_seed_corpus_documents_are_well_formed():
    docs = all_seed_documents()
    assert len(docs) == len(SOP_DOCUMENTS) + 1
    sources = [d["source"] for d in docs]
    assert len(sources) == len(set(sources)), "duplicate source names would overwrite each other"
    for doc in docs:
        assert doc["source"].strip()
        assert doc["content"].strip()


# --------------------------------------------------------------------------- #
# Graceful degradation (always runs)
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_retrieval_falls_back_to_memory_when_mongo_is_down(monkeypatch):
    async def _unavailable():
        return False

    monkeypatch.setattr(mongo_vector_store, "available", _unavailable)

    chunks = await hybrid_retriever.aretrieve("settlement delay IMPS payout", intent="SETTLEMENT")
    assert len(chunks) > 0
    assert "Settlement" in chunks[0]["source"]


@pytest.mark.anyio
async def test_retrieval_falls_back_when_mongo_search_raises(monkeypatch):
    async def _boom(*args, **kwargs):
        raise RuntimeError("connection reset by peer")

    monkeypatch.setattr(mongo_vector_store, "search", _boom)

    chunks = await hybrid_retriever.aretrieve("chargeback dispute window", intent="FAQ")
    assert len(chunks) > 0


@pytest.mark.anyio
async def test_seeding_is_skipped_cleanly_when_mongo_is_down(monkeypatch):
    async def _unavailable():
        return False

    monkeypatch.setattr(mongo_vector_store, "available", _unavailable)

    result = await ingest_service.seed_knowledge_base()
    assert result["seeded"] is False
    assert "unreachable" in result["reason"].lower()


@pytest.mark.anyio
async def test_status_reports_the_fallback_when_mongo_is_down(monkeypatch):
    async def _unavailable():
        return False

    monkeypatch.setattr(mongo_vector_store, "available", _unavailable)

    status = await mongo_vector_store.status()
    assert status["mongoReachable"] is False
    assert "in-memory" in status["fallback"]


def test_synchronous_retrieve_contract_is_unchanged():
    """Existing callers of the sync API must keep working."""
    chunks = hybrid_retriever.retrieve("settlement delay IMPS payout", intent="SETTLEMENT")
    assert len(chunks) > 0
    assert "hybrid_score" in chunks[0]
    assert "confidence_pct" in chunks[0]


@pytest.mark.anyio
async def test_ingest_rejects_empty_input():
    assert (await ingest_service.ingest_document("", "content"))["skipped"] is True
    assert (await ingest_service.ingest_document("doc.md", "   "))["skipped"] is True


# --------------------------------------------------------------------------- #
# Live MongoDB (skipped when unreachable)
# --------------------------------------------------------------------------- #

@pytest.mark.anyio
async def test_ingest_and_retrieve_against_live_mongo():
    if not await mongo_vector_store.available():
        pytest.skip("MongoDB is not reachable; skipping live RAG round-trip.")

    source = "PyTest RAG Fixture.md"
    content = """
    # Chargeback Escalation Matrix
    Page 2: A chargeback that stays unresolved beyond ten working days is escalated to the
    network dispute desk with the RRN, the UTR and the merchant bank statement extract.
    """

    try:
        result = await ingest_service.ingest_document(source, content, {"category": "test"})
        assert result["indexed"] > 0

        # Re-ingesting identical content must be a no-op.
        again = await ingest_service.ingest_document(source, content, {"category": "test"})
        assert again["skipped"] is True and again["reason"] == "unchanged"

        hits = await mongo_vector_store.search("chargeback escalation network dispute desk", top_k=3)
        assert any(h["source"] == source for h in hits)
        top = next(h for h in hits if h["source"] == source)
        assert top["page"] == 2
        assert "chargeback" in top["text"].lower()
    finally:
        await ingest_service.remove_document(source)

    assert all(h["source"] != source for h in await mongo_vector_store.search("chargeback", top_k=5))


@pytest.mark.anyio
async def test_seed_knowledge_base_against_live_mongo():
    if not await mongo_vector_store.available():
        pytest.skip("MongoDB is not reachable; skipping live seeding.")

    result = await ingest_service.seed_knowledge_base()
    assert result["seeded"] is True

    status = await mongo_vector_store.status()
    assert status["chunks"] > 0
    assert "DigiPay Assistant Boundaries.md" in status["sources"]
    assert "AePS Transaction Limits and Conduct SOP.pdf" in status["sources"]

    hits = await mongo_vector_store.search("what is the AePS single transaction limit", top_k=4)
    assert len(hits) > 0


@pytest.mark.anyio
async def test_domain_questions_retrieve_the_right_document(monkeypatch):
    """
    Retrieval accuracy guard. A domain question must reach its SOP, and a question
    about the assistant's own limits must reach the boundary document.
    """
    if not await mongo_vector_store.available():
        pytest.skip("MongoDB is not reachable; skipping retrieval accuracy check.")

    await ingest_service.seed_knowledge_base()

    expectations = [
        ("what is the AePS single transaction limit", "AePS Transaction Limits"),
        ("how long does a chargeback window last", "Chargeback"),
        ("my fingerprint scanner is not working", "Face RD"),
        ("how long does KYC approval take", "KYC"),
        ("what does PENDING status mean for my transaction", "Status Interpretation"),
        ("when will my NEFT settlement clear", "Settlement"),
        ("can you transfer money for me", "Boundaries"),
        ("are you allowed to block a user", "Boundaries"),
    ]

    misses = []
    for query, expected in expectations:
        hits = await hybrid_retriever.aretrieve(query, intent="FAQ", top_k=2)
        if not hits or expected.lower() not in hits[0]["source"].lower():
            misses.append((query, hits[0]["source"] if hits else "(none)"))

    assert misses == [], f"queries routed to the wrong document: {misses}"
