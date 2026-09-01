"""Local embedding model, loaded once per process.

Groq has no embeddings endpoint, so this stays local (sentence-transformers) —
no extra API key, no per-call cost. `lru_cache` means the (fairly slow) model
load happens once per worker process, not once per request.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str):
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=model_name)
