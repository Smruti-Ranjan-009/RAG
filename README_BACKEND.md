# RAG API (Phase-1 + 2 + 3) — Backend

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
│   ├── retrieval.py                  # hybrid (BM25 + vector) retrieval + cross-encoder re-ranking
│   ├── generation.py                 # Groq LLM + versioned prompt + citation enforcement
│   ├── pipeline.py                    # orchestrates the above; framework-agnostic
│   ├── prompts.py                         # loads versioned templates from prompts.yaml
│   ├── prompts.yaml                        # v1 (baseline) / v2 (citation-enforced) templates
│   ├── schemas.py                      # request/response models (also = OpenAPI schema)
│   └── main.py                          # FastAPI app: /ingest, /query, /health
├── tests/                      # pytest unit tests (no live API calls) — added by this drop-in
├── eval/                       # Phase-3: golden Q&A set + offline faithfulness evaluation
│   ├── golden_qa.json
│   └── run_eval.py
├── .github/workflows/
│   └── eval.yml                # runs eval/run_eval.py on every PR, fails the build below threshold
├── backend-requirements.txt    # backend deps (FastAPI etc.) — kept separate from
│                               # the notebook's requirements.txt on purpose
├── eval-requirements.txt       # ragas, for running eval/run_eval.py
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

**POST /ingest** — load `data/` (+ any `web_urls`), chunk, embed, store. Also
invalidates the cached BM25 index so hybrid retrieval sees the new chunks.
```json
{"web_urls": ["https://en.wikipedia.org/wiki/Retrieval-augmented_generation"], "reset": false}
```

**POST /query** — hybrid retrieval (BM25 + vector) → cross-encoder re-rank →
generate → citation enforcement.
```json
{"question": "What is this project about?", "k": 5}
```
Response now includes `accepted` and `reason`:
```json
{
  "answer": "...",
  "sources": [{"source": "...", "snippet": "...", "rerank_score": 4.21}],
  "accepted": true,
  "reason": null
}
```
`accepted: false` means citation enforcement declined the answer — either
the model signaled `INSUFFICIENT_CONTEXT`, or it cited a chunk number that
wasn't actually in the retrieved context (a hallucinated source). In that
case `answer` is a decline message and `sources` is empty, not the raw
(unverified) model output.

## Tests

```bash
pytest
```
Covers chunking, context formatting, schema validation, citation enforcement,
and versioned-prompt loading — no network calls, no Groq API key needed.

## Docker

Build and run from `RAG/` root (the Dockerfile expects that as its build context):

```bash
docker build -t rag-api .
docker run -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data rag-api
```

`data/` is mounted as a volume rather than baked into the image at build time
— it's your knowledge base and changes independently of the code, so you
don't need to rebuild the image every time you add a document.

## A dependency pin worth knowing about

`backend-requirements.txt` pins `langchain-community<0.4`. Newer releases
removed a class that `ragas` (Phase-3's eval framework) still hard-imports at
module load time — a known, currently-open upstream bug
([ragas#2745](https://github.com/vibrantlabsai/ragas/issues/2745)), not
something specific to this project. The pin keeps the API and the Phase-3
eval script running against one consistent, working environment. If a future
`ragas` release fixes this, the pin can be dropped.

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

## Phase-3: evaluation

`eval/golden_qa.json` + `eval/run_eval.py` run the golden Q&A set through the
actual live pipeline (`rag_app.pipeline.run_query_for_eval` — same retrieval,
re-ranking, generation, and enforcement code `/query` uses) and score two
things:

- **Coverage / decline accuracy** — did enforcement do the right thing?
  Questions the docs *can* answer should get answered; the deliberately
  out-of-scope questions should get declined. Checked directly, no LLM judge.
- **Faithfulness** — for every answer that *was* accepted, does `ragas`'
  `Faithfulness` metric (an LLM-as-judge check, reusing your Groq LLM as the
  judge) agree the claims are actually supported by the retrieved chunks?
  Declined answers are excluded on purpose — there's nothing to check
  faithfulness on if nothing was claimed.

Run it locally:
```bash
pip install -r backend-requirements.txt -r eval-requirements.txt
python eval/run_eval.py                       # default threshold: 0.7
python eval/run_eval.py --threshold 0.8        # stricter
```
Exits `0` (pass) or `1` (fail) — that's what lets `.github/workflows/eval.yml`
gate a PR on it.

**Important — `golden_qa.json` is a starter set, not the real thing.**
It has 18 pairs; `RAG.md` calls for 50–200. The 18 here are grounded only in
`RAG.md`'s own text (verifiable) plus 3 deliberate out-of-scope questions to
exercise enforcement's decline path — none are drawn from `resume.pdf` or
anything else in `data/`, since those need genuine manual verification
against your actual source documents, which is the whole point of a *golden*
set. Add real pairs following the same shape:
```json
{
  "id": "qa-019",
  "question": "...",
  "ground_truth": "...",
  "expect_answerable": true,
  "source": "resume.pdf"
}
```
`ground_truth` isn't used by the faithfulness metric itself (that only needs
`question` + `answer` + retrieved `contexts`), but keeping it lets you
eyeball whether the pipeline's actual answer matches what you expect, and
sets you up for additional `ragas` metrics later (e.g. `answer_correctness`)
that do use it.

**CI setup:** add a `GROQ_API_KEY` repository secret (Settings → Secrets and
variables → Actions) — the workflow needs it both to populate the vector
store's answers and as the judge LLM for faithfulness scoring. The workflow
also assumes `data/` is committed to the repo, since a fresh CI checkout has
no pre-existing `chroma_db/` (that's gitignored) and re-ingests from `data/`
on every run.

## A second dependency pin worth knowing about

`eval-requirements.txt` pins `ragas==0.3.9`. Newer `ragas` releases hard-import
a class that's been removed from current `langchain-community` — another
known, currently-open upstream bug
([ragas#2745](https://github.com/vibrantlabsai/ragas/issues/2745)), same
kind of issue as the `langchain-community<0.4` pin above. Both pins together
are the combination actually verified to work.
