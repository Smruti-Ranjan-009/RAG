"""Phase-2 retrieval: hybrid (BM25 + vector) search, plus cross-encoder re-ranking.

BM25 needs the full chunk text up front to build its index, unlike vector
search, which only needs a query embedding at search time. Rebuilding that
index from the vector store on every single request would be wasteful, so
it's cached in-memory here, keyed by collection name, and only rebuilt when
ingestion actually changes the collection — `pipeline.run_ingest` calls
`invalidate_bm25_cache` after every ingest to keep this correct.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_bm25_cache: dict[str, object] = {}


def _load_all_chunks(vectorstore) -> list[Document]:
    raw = vectorstore.get(include=["documents", "metadatas"])
    return [
        Document(page_content=text, metadata=meta or {})
        for text, meta in zip(raw["documents"], raw["metadatas"])
    ]


def _get_bm25_retriever(vectorstore, collection_name: str, k: int):
    from langchain_community.retrievers import BM25Retriever

    if collection_name not in _bm25_cache:
        chunks = _load_all_chunks(vectorstore)
        if not chunks:
            return None
        _bm25_cache[collection_name] = BM25Retriever.from_documents(chunks)
        logger.info("Built BM25 index for '%s' with %d chunks", collection_name, len(chunks))

    retriever = _bm25_cache[collection_name]
    retriever.k = k
    return retriever


def invalidate_bm25_cache(collection_name: str | None = None) -> None:
    """Call after any ingest that changes `collection_name`'s contents."""
    if collection_name is None:
        _bm25_cache.clear()
    else:
        _bm25_cache.pop(collection_name, None)


def retrieve_hybrid(
    vectorstore,
    collection_name: str,
    query: str,
    bm25_k: int = 5,
    vector_k: int = 5,
    weights: tuple[float, float] = (0.4, 0.6),
) -> list[Document]:
    """BM25 + vector search, merged via reciprocal rank fusion.

    Falls back to vector-only if the collection is empty or BM25 has nothing
    to index yet (e.g. right after a reset, before the first ingest).
    """
    from langchain_classic.retrievers import EnsembleRetriever

    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": vector_k})
    bm25_retriever = _get_bm25_retriever(vectorstore, collection_name, k=bm25_k)

    if bm25_retriever is None:
        return vector_retriever.invoke(query)

    hybrid = EnsembleRetriever(retrievers=[bm25_retriever, vector_retriever], weights=list(weights))
    return hybrid.invoke(query)


@lru_cache(maxsize=1)
def _get_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


def rerank(query: str, docs: list[Document], model_name: str, top_n: int = 5) -> list[Document]:
    """Re-scores each (query, chunk) pair jointly — more accurate than either
    retriever alone, which is why it only runs on the small candidate set
    hybrid retrieval already narrowed down, not the whole vector store."""
    if not docs:
        return []

    cross_encoder = _get_cross_encoder(model_name)
    pairs = [(query, d.page_content) for d in docs]
    scores = cross_encoder.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda pair: pair[1], reverse=True)
    reranked_docs = []
    for doc, score in ranked[:top_n]:
        doc.metadata["rerank_score"] = float(score)
        reranked_docs.append(doc)
    return reranked_docs
