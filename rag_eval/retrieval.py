"""RAG eval retrieval réteg.

A low-level retrieval (embed_text, search_pgvector) a kanonikus rag_core-ból jön.
Itt csak az eval-specifikus glue marad: teszteset betöltés és a base_id-alapú
dedup, ami a metrikákhoz (precision/recall) kell.
"""

from typing import Any, Dict, List, Tuple
import json
from dataclasses import dataclass

import psycopg

from rag_core.retrieval import embed_text, search_pgvector
from rag_eval.metrics import unique_base_ids_in_order

__all__ = [
    "EvalCase",
    "load_test_cases",
    "embed_text",
    "search_pgvector",
    "retrieve_baseline_or_chunked",
    "retrieve_chunked_rerank",
]


@dataclass
class EvalCase:
    id: str
    question: str
    expected_doc_ids: List[str]


def load_test_cases(path: str) -> List[EvalCase]:
    """Betölti a RAG teszteseteket JSON-ből (id, question, expected_doc_ids)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [
        EvalCase(
            id=str(c["id"]),
            question=c["question"],
            expected_doc_ids=[str(eid) for eid in c["expected_doc_ids"]],
        )
        for c in data
    ]


def retrieve_baseline_or_chunked(
    conn: psycopg.Connection,
    question: str,
    table_name: str,
    top_k: int,
    session_id=None,
    request_id=None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Baseline/chunked retrieval: tágabb jelöltlista + base_id dedup a metrikákhoz."""
    raw = search_pgvector(
        conn,
        question,
        top_k * 3,
        table_name,
        session_id=session_id,
        request_id=request_id,
    )
    ids = unique_base_ids_in_order(raw, top_k)
    return raw, ids


def retrieve_chunked_rerank(
    conn: psycopg.Connection,
    question: str,
    table_name: str,
    top_k: int,
    candidate_k: int,
    rerank_fn,
    session_id: str = None,
    request_id: str = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Chunked + rerank retrieval a metrikákhoz (jelöltek, reranked lista, base_id-k)."""
    candidates = search_pgvector(
        conn,
        question,
        candidate_k,
        table_name,
        session_id=session_id,
        request_id=request_id,
    )
    reranked = rerank_fn(
        question,
        candidates,
        top_n=top_k * 2,
        session_id=session_id,
        request_id=request_id,
    )
    ids = unique_base_ids_in_order(reranked, top_k)
    return candidates, reranked, ids
