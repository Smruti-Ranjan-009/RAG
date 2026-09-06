"""Orchestrates loaders -> chunking -> vectorstore -> hybrid retrieval ->
re-ranking -> citation-enforced generation.

Kept separate from main.py on purpose: this module has no FastAPI import, so
it's usable from a CLI script, a background worker, an eval script (Phase-3),
or a test file without spinning up a web server. main.py is a thin adapter
over this.
"""

from __future__ import annotations

import logging
from typing import Iterable

from .chunking import chunk_documents
from .config import Settings
from .generation import generate_answer, get_llm
from .loaders import load_all_documents
from .retrieval import invalidate_bm25_cache, rerank, retrieve_hybrid
from .schemas import IngestResponse, QueryResponse, SourceChunk
from .vectorstore import add_documents, get_vectorstore, reset_vectorstore

logger = logging.getLogger(__name__)

SNIPPET_LENGTH = 200


def run_ingest(settings: Settings, web_urls: Iterable[str] = (), reset: bool = False) -> IngestResponse:
    if reset:
        reset_vectorstore(settings.persist_dir)

    docs = load_all_documents(settings.data_dir, web_urls)
    if not docs:
        logger.warning("No documents found in %s (and no reachable web_urls)", settings.data_dir)

    chunks = chunk_documents(docs, settings.chunk_size_tokens, settings.chunk_overlap_tokens)

    vectorstore = get_vectorstore(settings.persist_dir, settings.collection_name, settings.embedding_model)
    stored = add_documents(vectorstore, chunks)

    # The BM25 index is a snapshot of the collection at build time — anything
    # this ingest just added (or removed, via reset) would be invisible to it
    # until the cache is dropped and rebuilt on the next query.
    invalidate_bm25_cache(settings.collection_name)

    return IngestResponse(
        documents_loaded=len(docs),
        chunks_created=len(chunks),
        chunks_stored=stored,
    )


def _run_query_core(settings: Settings, question: str, k: int | None = None) -> tuple[list, dict]:
    """Shared retrieval -> rerank -> generation logic. Returns (top_docs, result)
    where result is generate_answer's dict (final_answer/accepted/reason).

    Both run_query (API, truncated snippets) and run_query_for_eval (Phase-3,
    full chunk text) call this, so there's exactly one place the actual
    pipeline logic lives — no risk of the two drifting apart."""
    vectorstore = get_vectorstore(settings.persist_dir, settings.collection_name, settings.embedding_model)

    bm25_k = k or settings.bm25_k
    vector_k = k or settings.vector_k

    candidates = retrieve_hybrid(
        vectorstore,
        settings.collection_name,
        question,
        bm25_k=bm25_k,
        vector_k=vector_k,
        weights=settings.hybrid_weights,
    )

    if not candidates:
        # Empty vector store, or genuinely nothing relevant. Either way, don't
        # call the LLM with no context — it'll either hallucinate or the
        # prompt's honesty instruction will kick in, but why pay for the call.
        return [], {
            "final_answer": "No relevant documents found. Has the vector store been populated via /ingest?",
            "accepted": False,
            "reason": "no chunks retrieved",
        }

    top_docs = rerank(question, candidates, settings.cross_encoder_model, top_n=settings.rerank_top_n)

    llm = get_llm(settings.groq_model, settings.groq_api_key, settings.groq_temperature)
    result = generate_answer(llm, question, top_docs, prompt_version=settings.prompt_version)

    return top_docs, result


def run_query(settings: Settings, question: str, k: int | None = None) -> QueryResponse:
    top_docs, result = _run_query_core(settings, question, k)

    sources = (
        [
            SourceChunk(
                source=d.metadata.get("source", "unknown"),
                snippet=d.page_content[:SNIPPET_LENGTH],
                rerank_score=d.metadata.get("rerank_score"),
            )
            for d in top_docs
        ]
        if result["accepted"]
        else []
    )

    return QueryResponse(
        answer=result["final_answer"],
        sources=sources,
        accepted=result["accepted"],
        reason=result["reason"],
    )


def run_query_for_eval(settings: Settings, question: str, k: int | None = None) -> dict:
    """Like run_query, but returns full (untruncated) retrieved chunk text
    instead of the API's 200-char UI snippets. Phase-3's ragas faithfulness
    scoring needs the complete context the model actually saw — scoring
    against a truncated snippet would unfairly judge the model against text
    it never had access to."""
    top_docs, result = _run_query_core(settings, question, k)

    return {
        "question": question,
        "answer": result["final_answer"],
        "contexts": [d.page_content for d in top_docs],
        "accepted": result["accepted"],
        "reason": result["reason"],
    }
