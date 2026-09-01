"""Chroma vector store: open/create, add chunks, and reset.

`get_vectorstore` is intentionally cheap to call repeatedly — Chroma just
reopens the on-disk collection, it doesn't re-embed anything that's already
stored. The FastAPI layer caches the instance anyway (see main.py) so this
isn't on the hot path per-request, but it's safe if it were.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from langchain_core.documents import Document

from .embeddings import get_embedding_model

logger = logging.getLogger(__name__)


def get_vectorstore(persist_dir: Path, collection_name: str, embedding_model_name: str):
    from langchain_chroma import Chroma

    embeddings = get_embedding_model(embedding_model_name)
    return Chroma(
        persist_directory=str(persist_dir),
        collection_name=collection_name,
        embedding_function=embeddings,
    )


def add_documents(vectorstore, chunks: list[Document]) -> int:
    if not chunks:
        return 0
    vectorstore.add_documents(chunks)
    logger.info("Added %d chunks to vector store", len(chunks))
    return len(chunks)


def reset_vectorstore(persist_dir: Path) -> None:
    """Delete the on-disk collection. Caller is responsible for dropping any
    cached vectorstore instance/client reference afterwards."""
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
        logger.warning("Deleted vector store at %s", persist_dir)
    else:
        logger.info("No vector store at %s to delete", persist_dir)
