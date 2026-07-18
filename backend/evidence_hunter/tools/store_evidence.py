"""
StoreEvidence Tool
Chunks and stores web search results in ChromaDB for RAG retrieval.
"""

import hashlib
import json
import os

from pydantic import BaseModel, Field


# Module-level singleton for the embedding model (lazy-loaded)
_embedding_model = None


def _get_embedding_model():
    """Lazy-load the sentence transformer model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def _get_chroma_collection(session_id: str):
    """Get or create a ChromaDB collection for a session."""
    import chromadb

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
    client = chromadb.PersistentClient(path=persist_dir)
    collection_name = f"factlens_{session_id}"

    # ChromaDB collection names: 3-63 chars, alphanumeric + underscores
    collection_name = collection_name[:63]

    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap

    return chunks


class StoreEvidence(BaseModel):
    """
    Chunks web search results and stores them in the ChromaDB
    vector database for later retrieval. Uses sentence-transformers
    for embedding.
    """

    search_results_json: str = Field(
        ...,
        description=(
            "JSON string of search results to store. Should contain "
            "an array of objects with 'title', 'url', and 'content' fields."
        ),
    )
    session_id: str = Field(
        default="default",
        description="Session ID for scoping the vector store collection.",
    )

    def run(self) -> str:
        """Chunk and store evidence in ChromaDB."""
        try:
            data = json.loads(self.search_results_json)

            # Handle both {results: [...]} and [...] formats
            if isinstance(data, dict):
                results = data.get("results", [])
            elif isinstance(data, list):
                results = data
            else:
                return json.dumps({"stored": 0, "error": "Invalid format"})

            if not results:
                return json.dumps({"stored": 0, "message": "No results to store"})

            model = _get_embedding_model()
            collection = _get_chroma_collection(self.session_id)

            all_chunks = []
            all_metadatas = []
            all_ids = []

            for result in results:
                content = result.get("content", "")
                title = result.get("title", "")
                url = result.get("url", "")

                if not content:
                    continue

                # Chunk the content
                chunks = _chunk_text(content)

                for i, chunk in enumerate(chunks):
                    chunk_id = hashlib.md5(
                        f"{url}_{i}_{chunk[:50]}".encode()
                    ).hexdigest()

                    all_chunks.append(chunk)
                    all_metadatas.append({
                        "source_url": url,
                        "source_title": title,
                        "chunk_index": i,
                    })
                    all_ids.append(chunk_id)

            if not all_chunks:
                return json.dumps({"stored": 0, "message": "No content to chunk"})

            # Generate embeddings
            embeddings = model.encode(all_chunks).tolist()

            # Upsert into ChromaDB
            collection.upsert(
                ids=all_ids,
                embeddings=embeddings,
                documents=all_chunks,
                metadatas=all_metadatas,
            )

            return json.dumps({
                "stored": len(all_chunks),
                "session_id": self.session_id,
                "message": f"Stored {len(all_chunks)} evidence chunks from {len(results)} sources",
            })

        except Exception as e:
            return json.dumps({"stored": 0, "error": str(e)})
