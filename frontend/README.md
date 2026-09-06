# RAG Ledger — Frontend

A minimal React/Vite UI for the RAG API. Each question becomes a self-contained
entry: the answer with clickable, numbered citation chips, and an expandable
list of the exact source chunks those citations point to. Declined answers
(citation enforcement) get their own honest treatment instead of a generic
error.

## Layout

Sits alongside `rag_app/` in your `RAG/` project root:

```
RAG/
├── rag_app/          # backend
├── frontend/         # <- this
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── api.js           # calls /query and /health only — never /ingest
│   │   └── components/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
└── ...
```

## Why there's no ingest button

The UI only calls `/query` and `/health`. Exposing `/ingest` to anyone who
opens the page would let a stranger trigger re-ingestion — including
`reset: true`, which wipes your vector store — or just run up your Groq bill
by re-embedding repeatedly. Run ingestion yourself (via `/docs`, curl, or a
script) before deploying; the public frontend never touches it.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # points at your backend; defaults to localhost:8000
npm run dev
```

Make sure the backend is actually running first (`uvicorn rag_app.main:app --reload`
from `RAG/` root) and has already been ingested — an empty vector store means
every question comes back declined, which will look like a bug rather than
correct behavior.

## Deploying (Vercel)

1. Push `RAG/` to GitHub (or just the `frontend/` folder as its own repo).
2. In Vercel: New Project → import the repo → set **Root Directory** to
   `frontend` if it's part of the monorepo.
3. Add an environment variable: `VITE_API_BASE_URL` = your deployed backend's
   URL (e.g. the Render URL from deploying `rag_app/`).
4. Deploy. Vercel auto-detects Vite; no build config needed beyond the env var.

One thing to check after deploying: your backend's `CORS_ALLOW_ORIGINS`
(in its `.env`) needs to include your actual Vercel URL, not just
`localhost:5173` — otherwise the browser will block every request with a CORS
error, and it'll look like the backend is down when it's actually a
one-line config fix.

## What's here vs. what's not

This is intentionally a single-page demo, not a multi-page app — no routing,
no auth, no persisted history across page reloads. That matches what the
backend actually offers right now (stateless `/query` calls, no session or
user concept). Adding any of those is a backend decision first, not something
to bolt onto the frontend alone.
