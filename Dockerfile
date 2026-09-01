FROM python:3.12-slim

WORKDIR /app

# System deps needed by unstructured/pypdf/lxml at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend-requirements.txt .
RUN pip install --no-cache-dir -r backend-requirements.txt

COPY rag_app ./rag_app

# data/ is NOT baked into the image — it's your knowledge base, not code. Mount
# it at runtime instead (build + run both from the RAG/ project root):
#   docker build -t rag-api .
#   docker run -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data rag-api

# GROQ_API_KEY etc. are injected at runtime (docker run -e / docker-compose / Render env vars),
# never baked into the image.
EXPOSE 8000

CMD ["uvicorn", "rag_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
