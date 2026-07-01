"""rag_core — kanonikus RAG mag: közös adatmodell, retrieval, generation, pipeline."""

from .types import (
    RAGRequest,
    RAGResponse,
    RetrievalStrategy,
    RetrievedChunk,
)

__all__ = [
    "RAGRequest",
    "RAGResponse",
    "RetrievalStrategy",
    "RetrievedChunk",
]
