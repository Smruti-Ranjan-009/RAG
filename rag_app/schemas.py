"""Request/response models. Also doubles as the OpenAPI schema FastAPI
generates automatically at /docs — keep field descriptions accurate, your
React frontend's contract comes straight from this."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    web_urls: list[str] = Field(
        default_factory=list,
        description="Webpages to fetch and ingest alongside local files in data_dir.",
    )
    reset: bool = Field(
        default=False,
        description="If true, wipe the existing vector store before ingesting.",
    )


class IngestResponse(BaseModel):
    documents_loaded: int
    chunks_created: int
    chunks_stored: int


class SourceChunk(BaseModel):
    source: str
    snippet: str = Field(description="First ~200 chars of the retrieved chunk, for UI display.")
    rerank_score: float | None = Field(
        default=None, description="Cross-encoder relevance score, if re-ranking ran."
    )


class QueryRequest(BaseModel):
    question: str
    k: int | None = Field(
        default=None, description="Overrides both bm25_k and vector_k (pre-rerank candidate count) for this query."
    )


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    accepted: bool = Field(
        description="False if citation enforcement declined the answer (insufficient context or an "
        "invalid citation) — in that case `answer` is the decline message, and `sources` is empty."
    )
    reason: str | None = Field(
        default=None, description="Why enforcement declined, if accepted is False."
    )
