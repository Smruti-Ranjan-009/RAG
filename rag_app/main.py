"""FastAPI entrypoint. This is what your React/Vite frontend talks to.

Run locally:
    uvicorn rag_app.main:app --reload

Then open http://localhost:8000/docs for interactive API docs (auto-generated
from schemas.py) and http://localhost:8000/health as a liveness check.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .logging_config import configure_logging
from .pipeline import run_ingest, run_query
from .schemas import IngestRequest, IngestResponse, QueryRequest, QueryResponse

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG API",
    description="Phase-1 retrieval-augmented generation service.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,  # set via CORS_ALLOW_ORIGINS in prod, e.g. your Vercel domain
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
def health() -> dict:
    """Liveness check — used by Docker/Render/uptime monitors, not by the frontend."""
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse, tags=["pipeline"])
def ingest(req: IngestRequest) -> IngestResponse:
    """Load documents (data_dir + any web_urls), chunk, embed, and store them."""
    try:
        return run_ingest(settings, web_urls=req.web_urls, reset=req.reset)
    except Exception:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail="Ingest failed. Check server logs.")


@app.post("/query", response_model=QueryResponse, tags=["pipeline"])
def query(req: QueryRequest) -> QueryResponse:
    """Retrieve top-K chunks for `question` and generate a cited answer."""
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")
    try:
        return run_query(settings, question=req.question, k=req.k)
    except Exception:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail="Query failed. Check server logs.")
