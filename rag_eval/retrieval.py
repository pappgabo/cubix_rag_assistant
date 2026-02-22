from typing import List, Dict, Any, Tuple
import psycopg
from psycopg import sql
from openai import OpenAI
from config import OPENAI_API_KEY, EMBEDDING_MODEL
from monitoring.log_llm_usage import log_llm_usage, calc_cost_usd
from rag_eval.metrics import unique_base_ids_in_order
import datetime, json, time, uuid 
from dataclasses import dataclass
from monitoring.log_llm_usage import log_llm_usage



# ------------------------------------------------------------
# Teszteset reprezentációja
# ------------------------------------------------------------
@dataclass
class EvalCase:
    id: str
    question: str
    expected_doc_ids: List[str]


def load_test_cases(path: str) -> List[EvalCase]:
    """
    Betölti a RAG teszteseteket JSON-ből.
    Minden elem tartalmazza:
        - id
        - question
        - expected_doc_ids (a helyes dokumentumok base_id listája)
    """
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


# ------------------------------------------------------------
# OpenAI embedding kliens
# ------------------------------------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)


# ------------------------------------------------------------
# 1) EMBEDDING GENERÁLÁSA
# ------------------------------------------------------------
def embed_text(text: str, session_id=None, request_id=None) -> List[float]:
    start = time.perf_counter()
    r_id = request_id or str(uuid.uuid4())
    s_id = session_id or f"rag-eval-fallback-{uuid.uuid4().hex[:6]}"

    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text],
        encoding_format="float"
    )

    prompt_tokens = resp.usage.prompt_tokens
    # Az új, közös függvény használata a 8 tizedesjegyes precízióért
    cost_usd = calc_cost_usd(EMBEDDING_MODEL, prompt_tokens, 0)
    
    latency_ms = int((time.perf_counter() - start) * 1000)

    log_llm_usage({
        "timestamp":  datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
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
    })

    return resp.data[0].embedding


# ------------------------------------------------------------
# 2) PGVECTOR KERESÉS
# ------------------------------------------------------------
def search_pgvector(
    conn: psycopg.Connection,
    query: str,
    k: int,
    table: str,
    session_id: str | None = None, # Opcionális paraméter
    request_id: str | None = None  # Opcionális paraméter
) -> List[Dict[str, Any]]:
    """
    Lekérdezi a pgvector táblából a query embeddingjéhez legközelebb eső K dokumentumot.

    Paraméterek:
        conn  – aktív PostgreSQL kapcsolat
        query – felhasználói kérdés
        k     – hány találatot kérünk
        table – melyik táblában keresünk (baseline vagy chunked)

    Visszatér:
        Lista dict-ekkel, minden elem tartalmazza:
            doc_id, base_id, text, metadata, score
    """

    # 1) Embedding generálása a kérdésből
    emb = embed_text(query, session_id=session_id, request_id=request_id)

    # 2) Biztonságos SQL összeállítása (Identifier → SQL injection védelem)
    query_sql = sql.SQL(
        """
        SELECT doc_id, text, metadata,
               metadata->>'base_id' AS base_id,
               1 - (embedding <=> %s::vector) AS score   -- cosine similarity
        FROM {table_name}
        ORDER BY embedding <=> %s::vector               -- cosine distance
        LIMIT %s
        """
    ).format(table_name=sql.Identifier(table))

    # 3) Lekérdezés futtatása
    rows = conn.execute(query_sql, (emb, emb, k)).fetchall()

    # 4) Eredmények átalakítása Python-barát formára
    results: List[Dict[str, Any]] = []
    for doc_id, text, metadata, base_id, score in rows:
        results.append(
            {
                "doc_id": doc_id,
                # Ha nincs base_id (baseline pipeline), akkor a doc_id legyen a fallback
                "base_id": str(base_id) if base_id else str(doc_id),
                "text": text,
                "metadata": metadata,
                "score": float(score),
            }
        )
    return results


# ------------------------------------------------------------
# 3) BASELINE vagy CHUNKED PIPELINE RETRIEVAL
# ------------------------------------------------------------
def retrieve_baseline_or_chunked(
    conn: psycopg.Connection,
    question: str,
    table_name: str,
    top_k: int,
    session_id=None, # Új paraméter default értékkel
    request_id=None  # Új paraméter default értékkel
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Baseline vagy chunked pipeline lekérdezése pgvectorból.

    Lépések:
        1) top_k * 3 jelölt lekérése pgvectorból (tágabb jelöltlista)
        2) duplikált base_id-k kiszűrése
        3) top_k egyedi dokumentum kiválasztása

    Visszatér:
        raw  – a nyers pgvector találatok (chunkok vagy dokumentumok)
        ids  – a top_k egyedi base_id sorrendben
    """
    raw = search_pgvector(conn, question, top_k * 3, table_name, session_id=session_id, 
        request_id=request_id)
    ids = unique_base_ids_in_order(raw, top_k)
    return raw, ids


# ------------------------------------------------------------
# 4) CHUNKED + RERANK PIPELINE
# ------------------------------------------------------------
def retrieve_chunked_rerank(
    conn: psycopg.Connection,
    question: str,
    table_name: str,
    top_k: int,
    candidate_k: int,
    rerank_fn,
    session_id: str = None, 
    request_id: str = None  
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """
    Chunked + CrossEncoder reranking pipeline.

    Lépések:
        1) pgvector → candidate_k jelölt chunk
        2) CrossEncoder → reranking (top_k * 2)
        3) Egyedi base_id-k kiválasztása (top_k)

    Visszatér:
        candidates – a pgvector által adott jelöltek
        reranked   – a CrossEncoder által újrarendezett lista
        ids        – a top_k egyedi base_id sorrendben
    """

    # 1) Jelöltek lekérése pgvectorból
    candidates = search_pgvector(conn, question, candidate_k, table_name, session_id=session_id,
    request_id=request_id)

    # 2) Reranking CrossEncoderrel
    reranked = rerank_fn(question, candidates, top_n=top_k * 2, session_id=session_id, request_id=request_id)

    # 3) Egyedi dokumentumok kiválasztása
    ids = unique_base_ids_in_order(reranked, top_k)

    return candidates, reranked, ids
