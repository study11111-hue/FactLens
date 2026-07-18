# ── FactLens Backend — Dockerfile ────────────────────────────
# Single-stage build for reliability (avoids multi-stage native lib copy issues)

FROM python:3.11-slim

WORKDIR /app

# Install system deps (build tools + runtime libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps first (layer cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# Pre-download sentence-transformers model at build time
# so the first request is fast (avoids cold-start timeout)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
    && echo "✅ Embedding model downloaded"

# Create ChromaDB directory (Railway volume will mount here)
RUN mkdir -p /app/chroma_data

# Expose default port
EXPOSE 8000

# ── Start Command ─────────────────────────────────────────────
# Shell form ensures ${PORT:-8000} is properly expanded
# Railway injects PORT env var — we use it with 8000 as fallback
CMD sh -c "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info"
