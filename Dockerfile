FROM python:3.12-slim

WORKDIR /app

# System deps needed by unstructured/pypdf/lxml at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend-requirements.txt .
RUN pip install --no-cache-dir -r backend-requirements.txt

COPY rag_app ./rag_app
COPY data ./data

# Render's free tier has no persistent disk — every cold-start restart (after
# 15 min idle) begins with a completely fresh container, so anything written
# to disk during a previous run (the vector store) is gone. That's why data/
# IS baked into the image here (unlike an earlier version of this Dockerfile,
# which mounted it as a volume for local Docker runs where a fresh vectorstore
# every restart isn't the norm), and why ingestion runs automatically on every
# boot below instead of waiting for a manual POST /ingest call nobody's there
# to make right after a cold start.
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# GROQ_API_KEY etc. are injected at runtime (docker run -e / docker-compose / Render env vars),
# never baked into the image.
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
