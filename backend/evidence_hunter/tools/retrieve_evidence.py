"""
RetrieveEvidence Tool
Performs semantic search over ChromaDB to retrieve relevant evidence.
"""

import json
import os

from agency_swarm.tools import BaseTool
from pydantic import Field


# Reuse the same lazy-loading pattern for embedding model
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
    collection_name = f"factlens_{session_id}"[:63]

    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


class RetrieveEvidence(BaseTool):
    """
    Retrieves the most semantically relevant evidence chunks
    from ChromaDB for a given claim. Uses cosine similarity
    to rank results.
    """

    claim_text: str = Field(
        ...,
        description="The factual claim to retrieve evidence for.",
    )
    session_id: str = Field(
        default="default",
        description="Session ID for scoping the vector store collection.",
    )
    top_k: int = Field(
        default=5,
        description="Number of top evidence chunks to retrieve.",
    )

    def run(self) -> str:
        """Retrieve relevant evidence from ChromaDB."""
        try:
            model = _get_embedding_model()
            collection = _get_chroma_collection(self.session_id)

            # Check if collection has any data
            if collection.count() == 0:
                return json.dumps({
                    "claim": self.claim_text,
                    "evidence": [],
                    "message": "No evidence stored yet for this session",
                })

            # Generate embedding for the claim
            query_embedding = model.encode([self.claim_text]).tolist()

            # Query ChromaDB
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=min(self.top_k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            evidence_chunks = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0.0

                    # Convert cosine distance to similarity score
                    similarity = 1 - distance

                    evidence_chunks.append({
                        "text": doc,
                        "source_url": metadata.get("source_url", ""),
                        "source_title": metadata.get("source_title", ""),
                        "similarity_score": round(similarity, 4),
                    })

            return json.dumps({
                "claim": self.claim_text,
                "evidence": evidence_chunks,
                "total_stored": collection.count(),
            }, indent=2)

        except Exception as e:
            return json.dumps({
                "claim": self.claim_text,
                "evidence": [],
                "error": str(e),
            })
