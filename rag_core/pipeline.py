"""A kanonikus RAG pipeline: retrieve + generate -> RAGResponse.

Ezt hívja a prompt eval, és ezt (vagy ennek HTTP-façade-ját) hívná a prod is.
"""

from __future__ import annotations

from typing import Optional

import psycopg

from config import RAG_CHAT_MODEL

from .generation import generate_answer
from .retrieval import retrieve
from .types import RAGRequest, RAGResponse


def run_rag(
    request: RAGRequest,
    conn: Optional[psycopg.Connection] = None,
) -> RAGResponse:
    """Teljes RAG kör: kontextus lekérése + válasz generálása."""
    chunks = retrieve(request, conn=conn)

    answer = generate_answer(
        question=request.question,
        chunk_texts=[c.text for c in chunks],
        session_id=request.session_id,
        request_id=request.request_id,
        prompt_version=request.prompt_version,
    )

    return RAGResponse(
        answer=answer,
        chunks=chunks,
        strategy=request.strategy,
        model=RAG_CHAT_MODEL,
        prompt_version=request.prompt_version,
    )
