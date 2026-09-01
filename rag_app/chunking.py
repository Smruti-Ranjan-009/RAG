"""Split documents into token-bounded, overlapping chunks.

Token-based (not character-based) length so "500-800 tokens" means real model
tokens. Overlap keeps sentences that straddle a chunk boundary from losing
context in retrieval.
"""

from __future__ import annotations

from functools import lru_cache

import tiktoken
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


@lru_cache(maxsize=1)
def _encoding():
    return tiktoken.get_encoding("cl100k_base")


def token_len(text: str) -> int:
    return len(_encoding().encode(text))


def get_splitter(chunk_size: int = 700, chunk_overlap: int = 100) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=token_len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_documents(
    docs: list[Document],
    chunk_size: int = 700,
    chunk_overlap: int = 100,
) -> list[Document]:
    if not docs:
        return []
    splitter = get_splitter(chunk_size, chunk_overlap)
    return splitter.split_documents(docs)
