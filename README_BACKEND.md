# RAG API (Phase-1) — Backend

The notebook pipeline, restructured as a FastAPI service so a React/Vite frontend
(or anything else) can call it over HTTP instead of running cells by hand.

This lives directly in your `RAG/` project root, alongside `notebook_demo/` and
`data/` — not nested in its own subfolder — so it shares `data/` with the
notebook with no path juggling.

## Layout

```
RAG/
├── data/                       # shared source docs (pdfs, mds) — used by both
│                               # notebook_demo/ and rag_app/
├── notebook_demo/              # the exploratory notebook — untouched
├── rag_app/                    # <- the Python package (added by this drop-in)
│   ├── config.py                 # typed settings, loaded from .env
│   ├── logging_config.py         # one place to set up logging
│   ├── loaders.py                 # PDF / Markdown / web -> Document
│   ├── chunking.py                # token-aware splitting
│   ├── embeddings.py               # local embedding model (cached)
│   ├── vectorstore.py               # Chroma open/add/reset
│   ├── retrieval.py                  # top-K similarity search
│   ├── generation.py                 # Groq LLM + cited-answer prompt
│   ├── pipeline.py                    # orchestrates the above; framework-agnostic
│   ├── schemas.py                      # request/response models (also = OpenAPI schema)
│   └── main.py                          # FastAPI app: /ingest, /query, /health
├── tests/                      # pytest unit tests (no live API calls) — added by this drop-in
├── backend-requirements.txt    # backend deps (FastAPI etc.) — kept separate from
│                               # the notebook's requirements.txt on purpose
├── Dockerfile
├── .env.example
├── pyproject.toml              # makes `rag_app` pip-installable (pip install -e .)
├── README_BACKEND.md           # this file — named to not clobber your existing README.md
├── .env                        # your existing project .env — add GROQ_API_KEY etc. here too
├── .gitignore                  # append the entries below to your existing one
├── LICENSE
├── RAG.md
├── README.md
└── requirements.txt            # notebook's deps — unchanged
```

**Why two `requirements.txt` files instead of one:** the notebook's deps
(langchain, chromadb, sentence-transformers, no web framework) and the
backend's deps (that set plus FastAPI, uvicorn, pytest) are genuinely
different. Merging them means the notebook environment also installs a web
server it never uses. Install whichever one matches what you're doing:

```bash
pip install -r requirements.txt          # for the notebook
pip install -r backend-requirements.txt  # for the API
```

Each pipeline stage (loaders, chunking, embeddings, vectorstore, retrieval,
generation) is its own module with no FastAPI dependency — `pipeline.py` is
the only thing that wires them together, and `main.py` is a thin HTTP adapter
over `pipeline.py`. That means you can also drive the whole thing from a
plain Python script without touching the web layer:

```python
from rag_app.config import settings
from rag_app.pipeline import run_ingest, run_query

run_ingest(settings, web_urls=["https://en.wikipedia.org/wiki/Retrieval-augmented_generation"])
result = run_query(settings, "What is this project about?")
print(result.answer)
```

## Setup

Run all of this from the `RAG/` project root:

```bash
# merge the variables from .env.example into your existing .env
pip install -e .               # installs rag_app as an editable package
pip install -r backend-requirements.txt
```

**Note on `.env`:** `pydantic-settings` (used in `config.py`) reads from a
file literally named `.env` in the working directory by default. If you
already have a `.env` at `RAG/` root, just add `GROQ_API_KEY` and the other
variables from `.env.example` into it directly rather than creating a second
file.

## Run locally

From `RAG/` root:

```bash
uvicorn rag_app.main:app --reload
```

- Interactive API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

`DATA_DIR=data` in `.env.example` already resolves correctly here, since
`rag_app/` and `data/` are siblings under `RAG/` and uvicorn runs with `RAG/`
as the working directory.

## API

**POST /ingest** — load `data/` (+ any `web_urls`), chunk, embed, store.
```json
{"web_urls": ["https://en.wikipedia.org/wiki/Retrieval-augmented_generation"], "reset": false}
```

**POST /query** — retrieve top-K chunks and generate a cited answer.
```json
{"question": "What is this project about?", "k": 5}
```

## Tests

```bash
pytest
```
Unit tests cover chunking, context formatting, and schema validation — no
network calls, no Groq API key needed to run them.

## Docker

Build and run from `RAG/` root (the Dockerfile expects that as its build context):

```bash
docker build -t rag-api .
docker run -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data rag-api
```

`data/` is mounted as a volume rather than baked into the image at build time
— it's your knowledge base and changes independently of the code, so you
don't need to rebuild the image every time you add a document.

## Add to your existing `.gitignore`

Rather than a second `.gitignore` file, just append these lines to the one
already at `RAG/` root:

```
__pycache__/
*.pyc
.pytest_cache/
chroma_db/
*.egg-info/
.venv/
venv/
```
(`.env` is presumably already ignored there.)

## What's deliberately not here yet (see RAG.md)

- Hybrid retrieval (BM25 + semantic) and cross-encoder re-ranking — Phase-2
- Citation *enforcement* (refuse to answer when chunks don't support a claim) — Phase-2
- Golden eval set + `ragas` faithfulness scoring in CI — Phase-3
