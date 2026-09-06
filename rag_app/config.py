"""Centralized, typed configuration.

Every tunable that used to be a hardcoded variable in the notebook (model names,
chunk size, paths, k) lives here so the whole app has one source of truth, and so
it can be overridden per-environment (dev / staging / prod) via env vars or `.env`
without touching code.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Groq (generation) ---
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"
    groq_temperature: float = 0.0

    # --- Embeddings (local) ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Storage ---
    data_dir: Path = Path("data")
    persist_dir: Path = Path("chroma_db")
    collection_name: str = "rag_phase1"

    # --- Chunking ---
    chunk_size_tokens: int = 700  # midpoint of the 500-800 token target range
    chunk_overlap_tokens: int = 100

    # --- Retrieval (Phase-2: hybrid + re-ranking) ---
    retrieval_k: int = 5  # legacy: used by any caller still doing plain vector search
    bm25_k: int = 5
    vector_k: int = 5
    hybrid_weights: tuple[float, float] = (0.4, 0.6)  # (bm25, vector)
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_top_n: int = 5

    # --- Generation ---
    prompt_version: str = "v2"  # see prompts.yaml; "v1" has no citation enforcement

    # --- Misc ---
    user_agent: str = "rag-phase1-app/1.0"
    cors_allow_origins: list[str] = ["http://localhost:5173"]  # React/Vite dev server

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # raises a clear validation error at startup if GROQ_API_KEY is missing
