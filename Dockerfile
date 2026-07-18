# ── FactLens Backend — Dockerfile ────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (layer cached)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Create ChromaDB data dir (Railway volume mounts here)
RUN mkdir -p /app/chroma_data

EXPOSE 8000

# Shell form so ${PORT:-8000} is properly expanded by sh
CMD sh -c "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info"
