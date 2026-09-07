#!/bin/sh
set -e

echo "Ingesting documents from data/ before starting the server..."
python -c "
from rag_app.config import settings
from rag_app.pipeline import run_ingest

result = run_ingest(settings, reset=True)
print(result)
if result.chunks_stored == 0:
    raise SystemExit('Ingest produced 0 chunks — check that data/ was actually baked into the image.')
"

echo "Ingest complete. Starting server..."
exec uvicorn rag_app.main:app --host 0.0.0.0 --port 8000
