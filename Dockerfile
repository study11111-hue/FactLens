# ── FactLens Backend — Dockerfile ────────────────────────────
# Multi-stage build for a lean, fast production image

# ── Stage 1: Build ────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY backend/requirements.txt .

# Install into a prefix so we can copy cleanly
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install only runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy backend source
COPY backend/ .

# Pre-download sentence-transformers model at build time
# so the first request is fast (model is baked into the image)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Create directory for ChromaDB volume mount
RUN mkdir -p /app/chroma_data

# Railway injects PORT env var — expose it
EXPOSE 8000

# ── Start Command ─────────────────────────────────────────────
# Uses gunicorn with uvicorn workers for production
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
