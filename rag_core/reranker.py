"""CrossEncoder reranker — kanonikus implementáció.

A modell betöltése lusta (lazy), így a baseline pipeline nem húzza be a torchot.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import RERANKER_MODEL
from monitoring.log_llm_usage import log_llm_usage

_reranker_model = None


def _get_model():
    global _reranker_model
    if _reranker_model is None:
        from sentence_transformers import CrossEncoder

        _reranker_model = CrossEncoder(RERANKER_MODEL)
    return _reranker_model


def rerank_chunks(
    query: str,
    chunks: List[Dict],
    top_n: int,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> List[Dict]:
    """A pgvector találatokat újrarendezi egy CrossEncoder relevancia-pontszám alapján."""
    if not chunks:
        return []

    start = time.perf_counter()
    success = True
    error_msg = None
    reranked: List[Dict] = []

    try:
        pairs = [[query, c["text"]] for c in chunks]
        scores = _get_model().predict(pairs)

        for c, s in zip(chunks, scores):
            c["rerank_score"] = float(s)

        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

    except Exception as e:
        success = False
        error_msg = str(e)
        print(f"❌ Reranker error: {error_msg}")

    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_llm_usage(
            {
                "timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "sessionId": session_id,
                "requestId": request_id or str(uuid.uuid4()),
                "component": "rag-rerank",
                "model": RERANKER_MODEL,
                "provider": "local",
                "promptTokens": 0,
                "completionTokens": 0,
                "totalTokens": 0,
                "costUsd": 0.0,
                "latencyMs": latency_ms,
                "success": success,
                "errorMessage": error_msg,
            }
        )

    return reranked[:top_n]
