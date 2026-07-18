"""
FactLens Configuration
Loads environment variables and provides sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Groq LLM ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Tavily Web Search ─────────────────────────────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── ChromaDB (RAG Vector Store) ───────────────────────────
# On Railway: mount a volume at /app/chroma_data for persistence
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "/app/chroma_data")
CHROMA_COLLECTION_PREFIX = "factlens_session"

# ── Embedding Model ──────────────────────────────────────
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
)

# ── RAG Pipeline Settings ────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))

# ── Server Settings ──────────────────────────────────────
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
# Railway injects PORT env var — read it first, fall back to SERVER_PORT
SERVER_PORT = int(os.getenv("PORT") or os.getenv("SERVER_PORT", "8000"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # "production" on Railway
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "chrome-extension://*,http://localhost:*,https://meet.google.com"
).split(",")

# ── Fact-Check Settings ──────────────────────────────────
VERDICT_CATEGORIES = ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
CAPTION_DEBOUNCE_MS = int(os.getenv("CAPTION_DEBOUNCE_MS", "3000"))
