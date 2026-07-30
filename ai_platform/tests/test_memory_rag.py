import pytest
from memory.ranking import memory_ranking_manager
from memory.semantic import semantic_memory_engine
from rag.chunker import document_chunker
from rag.vector_db import VectorDBStore
from rag.hybrid_retriever import hybrid_retriever
from rag.citation_engine import citation_engine

def test_memory_importance_ranking():
    rev_score = memory_ranking_manager.calculate_importance("REVERSAL")
    faq_score = memory_ranking_manager.calculate_importance("FAQ")
    assert rev_score == 9.5
    assert faq_score == 3.0

    meta = memory_ranking_manager.record_session_lifecycle(
        session_id="session_rank_test",
        intent="REVERSAL",
        tool_name="reverseTransaction",
        merchant_id="500100100014",
        user_id="user_123",
        tokens_used=450
    )
    assert meta["importance"] == 9.5
    assert meta["conversationTokens"] >= 450

def test_semantic_memory_search():
    matches = semantic_memory_engine.search_similar_resolutions(
        query="settlement delay stuck",
        merchant_id="500100100014"
    )
    assert len(matches) > 0
    assert "IMPS" in matches[0]["resolution"]

def test_document_chunker():
    doc = """
    # Section 1
    Page 1: Overview of Digipay Platform.
    Page 2: Settlement cycles happen T+1.
    """
    chunks = document_chunker.chunk_document(doc, "test_doc.pdf", chunk_size=10, overlap=2)
    assert len(chunks) > 0
    assert chunks[0]["source"] == "test_doc.pdf"

def test_vector_db_similarity():
    vdb = VectorDBStore()
    vdb.add_chunks([
        {"chunk_id": "c1", "text": "wallet balance enquiry info", "source": "s1.pdf", "section": "Sec 1", "page": 1},
        {"chunk_id": "c2", "text": "settlement IMPS payout delay", "source": "s2.pdf", "section": "Sec 2", "page": 2}
    ])
    res = vdb.similarity_search("wallet balance")
    assert len(res) > 0
    assert res[0]["chunk_id"] == "c1"

def test_hybrid_retrieval_and_citations():
    chunks = hybrid_retriever.retrieve("settlement delay IMPS payout", intent="SETTLEMENT")
    assert len(chunks) > 0
    assert "Settlement" in chunks[0]["source"]

    # Citations are user-facing, so they name the document and page in plain
    # words. The old format ("Sources & Provenance", per-chunk "Confidence: 84%")
    # exposed retrieval internals to a VLE and invited the wrong reading — a
    # similarity score is not the answer's correctness. Scores remain on the API
    # response and in logs for tuning.
    citations = citation_engine.format_citations(chunks)
    assert "Source" in citations
    assert "page" in citations
    assert "Settlement" in citations
    assert "Confidence" not in citations
    assert ".pdf" not in citations, "storage detail should not be shown to users"
