"""Backward-compat re-export. A kanonikus reranker a rag_core.reranker-ben van."""

from rag_core.reranker import rerank_chunks

__all__ = ["rerank_chunks"]
