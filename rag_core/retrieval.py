"""Kanonikus retrieval: embedding + pgvector keresés + opcionális rerank.

Ez az EGY retrieval implementáció. A rag_eval a low-level függvényeket
(embed_text, search_pgvector) innen importálja, a pipeline pedig a magas szintű
retrieve()-t hívja.
"""

from __future__ import annotations

import datetime
import time
import uuid
from typing import Any, Dict, List, Optional

import psycopg
from openai import OpenAI
from psycopg import sql

from config import (
    DOCUMENTS_BASELINE_TABLE,
    DOCUMENTS_CHUNKS_TABLE,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    PG_DSN,
    RAG_CANDIDATE_MULTIPLIER,
)
from monitoring.log_llm_usage import log_llm_usage, calc_cost_usd

from .types import RAGRequest, RetrievalStrategy, RetrievedChunk

_client = OpenAI(api_key=OPENAI_API_KEY)


def embed_text(
    text: str,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> List[float]:
    """Egyetlen szöveg embeddingje egységes LLM-usage logolással."""
    start = time.perf_counter()
    r_id = request_id or str(uuid.uuid4())
    s_id = session_id or f"rag-fallback-{uuid.uuid4().hex[:6]}"

    resp = _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text],
        encoding_format="float",
    )

    prompt_tokens = resp.usage.prompt_tokens
    cost_usd = calc_cost_usd(EMBEDDING_MODEL, prompt_tokens, 0)
    latency_ms = int((time.perf_counter() - start) * 1000)

    log_llm_usage(
        {
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "requestId": r_id,
            "sessionId": s_id,
            "component": "rag-embed",
            "model": EMBEDDING_MODEL,
            "provider": "openai",
            "promptTokens": prompt_tokens,
            "completionTokens": 0,
            "totalTokens": prompt_tokens,
            "costUsd": cost_usd,
            "latencyMs": latency_ms,
            "success": True,
        }
    )

    return resp.data[0].embedding


def search_pgvector(
    conn: psycopg.Connection,
    query: str,
    k: int,
    table: str,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """A query embeddingjéhez legközelebbi k sor lekérése pgvectorból."""
    emb = embed_text(query, session_id=session_id, request_id=request_id)

    query_sql = sql.SQL(
        """
        SELECT doc_id, text, metadata,
               metadata->>'base_id' AS base_id,
               1 - (embedding <=> %s::vector) AS score
        FROM {table_name}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """
    ).format(table_name=sql.Identifier(table))

    rows = conn.execute(query_sql, (emb, emb, k)).fetchall()

    results: List[Dict[str, Any]] = []
    for doc_id, text, metadata, base_id, score in rows:
        results.append(
            {
                "doc_id": doc_id,
                "base_id": str(base_id) if base_id else str(doc_id),
                "text": text,
                "metadata": metadata or {},
                "score": float(score),
            }
        )
    return results


def _table_for_strategy(strategy: RetrievalStrategy) -> str:
    if strategy == RetrievalStrategy.BASELINE:
        return DOCUMENTS_BASELINE_TABLE
    return DOCUMENTS_CHUNKS_TABLE


def retrieve(
    request: RAGRequest,
    conn: Optional[psycopg.Connection] = None,
) -> List[RetrievedChunk]:
    """Magas szintű retrieval: RAGRequest -> RetrievedChunk lista.

    A stratégia szerint választ táblát és eldönti, kell-e reranking.
    Ha nincs átadva kapcsolat, nyit egyet a PG_DSN alapján.
    """
    if conn is None:
        with psycopg.connect(PG_DSN) as owned_conn:
            return retrieve(request, conn=owned_conn)

    table = _table_for_strategy(request.strategy)

    if request.strategy == RetrievalStrategy.CHUNKED_RERANK:
        candidate_k = request.top_k * RAG_CANDIDATE_MULTIPLIER
        candidates = search_pgvector(
            conn,
            request.question,
            candidate_k,
            table,
            session_id=request.session_id,
            request_id=request.request_id,
        )
        from .reranker import rerank_chunks

        rows = rerank_chunks(
            request.question,
            candidates,
            top_n=request.top_k,
            session_id=request.session_id,
            request_id=request.request_id,
        )
    else:
        rows = search_pgvector(
            conn,
            request.question,
            request.top_k,
            table,
            session_id=request.session_id,
            request_id=request.request_id,
        )

    return [
        RetrievedChunk(
            doc_id=row["doc_id"],
            base_id=row["base_id"],
            text=row["text"],
            score=row.get("score", 0.0),
            rerank_score=row.get("rerank_score"),
            metadata=row.get("metadata", {}),
        )
        for row in rows
    ]
