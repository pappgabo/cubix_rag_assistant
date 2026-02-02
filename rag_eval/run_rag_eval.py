import json
from dataclasses import dataclass
from typing import List, Dict, Any, Set, Tuple
import sys
from pathlib import Path
from reranker import rerank_chunks
import psycopg
from psycopg import sql
from openai import OpenAI


# ------------------------------------------------------------
# A projekt gyökérkönyvtárának hozzáadása az import úthoz
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
   sys.path.append(str(ROOT))

# ------------------------------------------------------------
# Konfigurációk betöltése
# ------------------------------------------------------------
from config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    PG_DSN,
    RAG_TESTS_PATH,
    RAG_RESULTS_PATH,
    RAG_TOP_K,
)

# OpenAI kliens (embeddinghez)
client = OpenAI(api_key=OPENAI_API_KEY)

# Metrika szintű K (P@K, R@K, Hit@K, MRR@K ehhez igazodik)
TOP_K = RAG_TOP_K

# Rerankernek szánt jelöltek száma (széles merítés)
CANDIDATE_K = TOP_K * 4  # pl. TOP_K=5 → 20 jelölt

# ------------------------------------------------------------
# Pipeline → PostgreSQL tábla neve
# ------------------------------------------------------------
PIPELINES = {
    "baseline": "documents_baseline",   # teljes dokumentum
    "chunked": "documents_chunks",      # chunkolt, pgvector rangsor
    # "chunked_rerank" NEM táblához kötött külön, ugyanúgy documents_chunks-t használjuk
}

# ------------------------------------------------------------
# Teszteset struktúra
# ------------------------------------------------------------
@dataclass
class RagTestCase:
    id: str
    question: str
    expected_doc_ids: List[str]


# ------------------------------------------------------------
# Tesztesetek beolvasása JSON-ből
# ------------------------------------------------------------
def load_test_cases(path: str) -> List[RagTestCase]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        RagTestCase(
            id=item["id"],
            question=item["question"],
            expected_doc_ids=item.get("expected_doc_ids", []),
        )
        for item in data
    ]


# ------------------------------------------------------------
# Embedding generálás OpenAI-val
# ------------------------------------------------------------
def embed_text(text: str) -> List[float]:
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text],
        encoding_format="float",
    )
    return resp.data[0].embedding


# ------------------------------------------------------------
# Paraméterezhető pgvector keresés
# ------------------------------------------------------------
def search_pgvector(
    conn: psycopg.Connection,
    query: str,
    k: int,
    table: str,
) -> List[Dict[str, Any]]:
    """
    Lekérdezi a pgvector táblából a kérdéshez legközelebb eső K dokumentumot/chunkot.

    Paraméterek:
        conn  – aktív psycopg adatbázis kapcsolat
        query – a felhasználó kérdése (szöveg)
        k     – hány találatot kérünk (pl. 20 a rerankinghez)
        table – melyik táblából keresünk (baseline vagy chunked)

    Visszatér:
        Lista dict-ekkel, minden elem:
        {
            "doc_id": ...,
            "base_id": ...,
            "text": ...,
            "metadata": ...,
            "score": float
        }
    """

    # 1. A kérdés embeddingjének előállítása
    emb = embed_text(query)

    # 2. Biztonságos SQL összeállítása (Identifier → SQL injection védelem)
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

    # 3. Lekérdezés futtatása
    #    A psycopg automatikusan konvertálja a Python listát PostgreSQL vector típusra.
    rows = conn.execute(query_sql, (emb, emb, k)).fetchall()

    # 4. Eredmények átalakítása Python-barát formára
    results = []
    for doc_id, text, metadata, base_id, score in rows:
        results.append({
            "doc_id": doc_id,        # chunk vagy dokumentum egyedi ID
            "base_id": base_id,      # eredeti dokumentum ID (RAG eval miatt fontos)
            "text": text,            # chunk vagy dokumentum szövege
            "metadata": metadata,    # extra metaadatok
            "score": float(score),   # cosine similarity (0–1 között)
        })

    return results



# ------------------------------------------------------------
# Precision@K és Recall@K
# ------------------------------------------------------------
def precision_recall_at_k(
    expected: Set[str], retrieved: List[str], k: int
) -> Tuple[float, float]:
    top_k = retrieved[:k]

    if not expected:
        return 0.0, 0.0

    hits = sum(1 for doc_id in top_k if doc_id in expected)

    precision = hits / max(len(top_k), 1)
    recall = hits / len(expected)

    return precision, recall


# ------------------------------------------------------------
# Hit@K (Success@K)
# ------------------------------------------------------------
def hit_at_k(expected: Set[str], retrieved: List[str], k: int) -> float:
    if not expected:
        return 0.0
    top_k = retrieved[:k]
    return 1.0 if any(doc_id in expected for doc_id in top_k) else 0.0


# ------------------------------------------------------------
# MRR@K (Mean Reciprocal Rank)
# ------------------------------------------------------------
def mrr_at_k(expected: Set[str], retrieved: List[str], k: int) -> float:
    if not expected:
        return 0.0
    top_k = retrieved[:k]
    for rank, doc_id in enumerate(top_k, start=1):
        if doc_id in expected:
            return 1.0 / rank
    return 0.0


# ------------------------------------------------------------
# Chunk → dokumentum szintű ID-k
# ------------------------------------------------------------
def unique_base_ids_in_order(retrieved: List[Dict[str, Any]], k: int) -> List[str]:
    seen = set()
    ordered: List[str] = []

    for r in retrieved:
        base_id = r.get("base_id") or r.get("doc_id")
        if not base_id or base_id in seen:
            continue
        seen.add(base_id)
        ordered.append(base_id)
        if len(ordered) >= k:
            break

    return ordered

# ------------------------------------------------------------
# A teljes RAG értékelési pipeline
# ------------------------------------------------------------
def run_rag_eval():
    cases = load_test_cases(str(RAG_TESTS_PATH))
    print(f"Betöltött tesztesetek száma: {len(cases)}")

    all_results: Dict[str, Any] = {}

    with psycopg.connect(PG_DSN) as conn:
        # ------------------------------
        # 1) Baseline és chunked
        # ------------------------------
        for pipeline_name, table_name in PIPELINES.items():
            print(f"\n=== Pipeline futtatása: {pipeline_name} ({table_name}) ===")

            total_prec = total_rec = 0.0
            total_hit = total_mrr = 0.0
            n_with_gt = 0

            pipeline_results = []

            for case in cases:
                expected_set = set(case.expected_doc_ids)

                # Baseline: TOP_K * 3; Chunked: ugyanaz a logika
                retrieved = search_pgvector(
                    conn, case.question, TOP_K * 3, table_name
                )

                retrieved_ids = unique_base_ids_in_order(retrieved, TOP_K)

                prec, rec = precision_recall_at_k(
                    expected_set, retrieved_ids, TOP_K
                )
                hit = hit_at_k(expected_set, retrieved_ids, TOP_K)
                mrr = mrr_at_k(expected_set, retrieved_ids, TOP_K)

                if expected_set:
                    total_prec += prec
                    total_rec += rec
                    total_hit += hit
                    total_mrr += mrr
                    n_with_gt += 1

                print(
                    f"[{pipeline_name}][{case.id}] "
                    f"P@{TOP_K}={prec:.3f}, R@{TOP_K}={rec:.3f}, "
                    f"Hit@{TOP_K}={hit:.3f}, MRR@{TOP_K}={mrr:.3f}, "
                    f"expected={list(expected_set)}, retrieved={retrieved_ids}"
                )

                pipeline_results.append(
                    {
                        "id": case.id,
                        "question": case.question,
                        "expected_doc_ids": case.expected_doc_ids,
                        "retrieved": retrieved,
                        "precision_at_k": prec,
                        "recall_at_k": rec,
                        "hit_at_k": hit,
                        "mrr_at_k": mrr,
                    }
                )

            if n_with_gt:
                avg_prec = total_prec / n_with_gt
                avg_rec = total_rec / n_with_gt
                avg_hit = total_hit / n_with_gt
                avg_mrr = total_mrr / n_with_gt
            else:
                avg_prec = avg_rec = avg_hit = avg_mrr = 0.0

            all_results[pipeline_name] = {
                "summary": {
                    "top_k": TOP_K,
                    "num_cases": len(cases),
                    "num_cases_with_ground_truth": n_with_gt,
                    "avg_precision_at_k": avg_prec,
                    "avg_recall_at_k": avg_rec,
                    "avg_hit_at_k": avg_hit,
                    "avg_mrr_at_k": avg_mrr,
                },
                "cases": pipeline_results,
            }

        # ------------------------------
        # 2) Chunked + reranking pipeline
        # ------------------------------
        rerank_pipeline_name = "chunked_rerank"
        table_name = "documents_chunks"

        print(
            f"\n=== Pipeline futtatása: {rerank_pipeline_name} "
            f"({table_name}, CANDIDATE_K={CANDIDATE_K}) ==="
        )

        total_prec = total_rec = 0.0
        total_hit = total_mrr = 0.0
        n_with_gt = 0

        pipeline_results = []

        for case in cases:
            expected_set = set(case.expected_doc_ids)

            # Szélesebb merítés candidate-nek
            candidates = search_pgvector(
                conn, case.question, CANDIDATE_K, table_name
            )

            # Reranking Cross-Encoderrel (Itt legyen több, mint TOP_K, amiatt, hogy nagyobb eséllyel találjunk pontos találatot)
            reranked = rerank_chunks(case.question, candidates, TOP_K * 2)

            # Dokumentum-szintű ID-k a rerankelt top-K-ból
            retrieved_ids = unique_base_ids_in_order(reranked, TOP_K)

            prec, rec = precision_recall_at_k(
                expected_set, retrieved_ids, TOP_K
            )
            hit = hit_at_k(expected_set, retrieved_ids, TOP_K)
            mrr = mrr_at_k(expected_set, retrieved_ids, TOP_K)

            if expected_set:
                total_prec += prec
                total_rec += rec
                total_hit += hit
                total_mrr += mrr
                n_with_gt += 1

            print(
                f"[{rerank_pipeline_name}][{case.id}] "
                f"P@{TOP_K}={prec:.3f}, R@{TOP_K}={rec:.3f}, "
                f"Hit@{TOP_K}={hit:.3f}, MRR@{TOP_K}={mrr:.3f}, "
                f"expected={list(expected_set)}, retrieved={retrieved_ids}"
            )

            pipeline_results.append(
                {
                    "id": case.id,
                    "question": case.question,
                    "expected_doc_ids": case.expected_doc_ids,
                    "retrieved_candidates": candidates,
                    "reranked": reranked,
                    "precision_at_k": prec,
                    "recall_at_k": rec,
                    "hit_at_k": hit,
                    "mrr_at_k": mrr,
                }
            )


        if n_with_gt:
            avg_prec = total_prec / n_with_gt
            avg_rec = total_rec / n_with_gt
            avg_hit = total_hit / n_with_gt
            avg_mrr = total_mrr / n_with_gt

            avg_f1 = (2 * avg_prec * avg_rec / (avg_prec + avg_rec)
                if (avg_prec + avg_rec) > 0
                else 0.0
            )
        else:
            avg_prec = avg_rec = avg_hit = avg_mrr = avg_f1 = 0.0
    

        all_results[rerank_pipeline_name] = {
            "summary": {
                "top_k": TOP_K,
                "candidate_k": CANDIDATE_K,
                "num_cases": len(cases),
                "num_cases_with_ground_truth": n_with_gt,
                "avg_precision_at_k": avg_prec,
                "avg_recall_at_k": avg_rec,
                "avg_hit_at_k": avg_hit,
                "avg_mrr_at_k": avg_mrr,
                "avg_f1_at_k": avg_f1,
            },
            "cases": pipeline_results,
        }

    # ------------------------------------------------------------
    # Eredmények mentése JSON-be
    # ------------------------------------------------------------
    RAG_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAG_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\nEredmények elmentve ide: {RAG_RESULTS_PATH}")


if __name__ == "__main__":
    run_rag_eval()
