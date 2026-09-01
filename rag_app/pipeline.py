"""Orchestrates loaders -> chunking -> vectorstore -> retrieval -> generation.

Kept separate from main.py on purpose: this module has no FastAPI import, so
it's usable from a CLI script, a background worker, or a test file without
spinning up a web server. main.py is a thin adapter over this.
"""

from __future__ import annotations

import logging
from typing import Iterable

from .chunking import chunk_documents
from .config import Settings
from .generation import generate_answer, get_llm
from .loaders import load_all_documents
from .retrieval import retrieve
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

    return IngestResponse(
        documents_loaded=len(docs),
        chunks_created=len(chunks),
        chunks_stored=stored,
    )


def run_query(settings: Settings, question: str, k: int | None = None) -> QueryResponse:
    vectorstore = get_vectorstore(settings.persist_dir, settings.collection_name, settings.embedding_model)
    docs = retrieve(vectorstore, question, k=k or settings.retrieval_k)

    if not docs:
        # Empty vector store, or genuinely nothing relevant. Either way, don't
        # call the LLM with no context — it'll either hallucinate or the
        # prompt's honesty instruction will kick in, but why pay for the call.
        return QueryResponse(
            answer="No relevant documents found. Has the vector store been populated via /ingest?",
            sources=[],
        )

    llm = get_llm(settings.groq_model, settings.groq_api_key, settings.groq_temperature)
    answer = generate_answer(llm, question, docs)

    sources = [
        SourceChunk(source=d.metadata.get("source", "unknown"), snippet=d.page_content[:SNIPPET_LENGTH])
        for d in docs
    ]
    return QueryResponse(answer=answer, sources=sources)
