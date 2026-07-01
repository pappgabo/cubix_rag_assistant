"""A RAG rendszer közös adatmodellje (a korábban "contract"-nak nevezett réteg).

Ez a be- és kimenet hivatalos formája. Minden RAG-hívó (prompt eval, rag eval,
később a prod API) ezeket a típusokat használja, hogy ne legyen három külön
RAG-logika.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config import RAG_TOP_K


class RetrievalStrategy(str, Enum):
    """Milyen retrieval pipeline fusson."""

    BASELINE = "baseline"
    CHUNKED = "chunked"
    CHUNKED_RERANK = "chunked_rerank"


class RetrievedChunk(BaseModel):
    """Egy visszakeresett dokumentum/chunk a kontextusban."""

    doc_id: str
    base_id: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGRequest(BaseModel):
    """A RAG rendszer bemenete."""

    question: str
    session_id: str
    request_id: Optional[str] = None
    top_k: int = RAG_TOP_K
    strategy: RetrievalStrategy = RetrievalStrategy.BASELINE
    # Prompt életciklus: "prod" -> prompts/rag/system.txt,
    # egyébként prompts/rag/experiments/<prompt_version>.txt
    prompt_version: str = "prod"


class RAGResponse(BaseModel):
    """A RAG rendszer kimenete."""

    answer: str
    chunks: List[RetrievedChunk] = Field(default_factory=list)
    strategy: RetrievalStrategy = RetrievalStrategy.BASELINE
    model: str = ""
    prompt_version: str = "prod"
