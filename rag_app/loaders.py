"""Load raw documents from local files (PDF, Markdown) and webpages.

Kept deliberately dumb: each function returns a list of LangChain `Document`
objects with `source` set in metadata. No chunking, no embedding here — single
responsibility, easy to unit test, easy to swap a loader out later.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# WebBaseLoader warns loudly if this isn't set; harmless default so it never blocks anything.
os.environ.setdefault("USER_AGENT", "rag-phase1-app/1.0")


def load_local_documents(data_dir: Path) -> list[Document]:
    """Walk `data_dir` and load every .pdf and .md/.markdown file found."""
    from langchain_community.document_loaders import PyPDFLoader, UnstructuredMarkdownLoader

    docs: list[Document] = []

    if not data_dir.exists():
        logger.warning("data_dir %s does not exist; skipping local load", data_dir)
        return docs

    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        try:
            if suffix == ".pdf":
                loader = PyPDFLoader(str(path))
            elif suffix in (".md", ".markdown"):
                loader = UnstructuredMarkdownLoader(str(path))
            else:
                continue
            loaded = loader.load()
            for d in loaded:
                d.metadata["source"] = str(path)
            docs.extend(loaded)
            logger.info("Loaded %d document(s) from %s", len(loaded), path)
        except Exception:
            # A single bad file shouldn't take down the whole ingest run.
            logger.exception("Failed to load %s, skipping", path)

    return docs


def load_web_documents(urls: Iterable[str]) -> list[Document]:
    """Fetch and parse each URL. Failures are logged and skipped, not raised."""
    from langchain_community.document_loaders import WebBaseLoader

    urls = [u for u in urls if u and u.strip()]
    if not urls:
        return []

    docs: list[Document] = []
    for url in urls:
        try:
            loaded = WebBaseLoader(url).load()
            for d in loaded:
                d.metadata["source"] = d.metadata.get("source", url)
            docs.extend(loaded)
            logger.info("Loaded %d document(s) from %s", len(loaded), url)
        except Exception:
            logger.exception("Failed to load web document %s, skipping", url)

    return docs


def load_all_documents(data_dir: Path, web_urls: Iterable[str] = ()) -> list[Document]:
    """Convenience wrapper combining local + web sources for a single ingest pass."""
    return load_local_documents(data_dir) + load_web_documents(web_urls)
