"""Top-K retrieval on top of the vector store.

Thin on purpose — Phase-2 hybrid retrieval (BM25 + semantic) and re-ranking
slot in here without touching loaders, chunking, or generation.
"""

from __future__ import annotations

from langchain_core.documents import Document


def retrieve(vectorstore, query: str, k: int = 5) -> list[Document]:
    return vectorstore.similarity_search(query, k=k)
