import json
from dataclasses import dataclass
from typing import List, Dict, Any, Set, Tuple

import psycopg
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    PG_DSN,
    RAG_TESTS_PATH,
    RAG_RESULTS_PATH,
    RAG_TOP_K,
)

# OpenAI kliens inicializálása a megadott API kulccsal.
client = OpenAI(api_key=OPENAI_API_KEY)

# A visszaadandó dokumentumok száma (TOP-K keresés)
TOP_K = RAG_TOP_K


# --- Tesztesetek adatszerkezete ---

@dataclass
class RagTestCase:
    """
    Egyetlen RAG teszteset:
    - id: azonosító
    - question: a felhasználói kérdés
    - expected_doc_ids: a helyes dokumentumok ID-i (ground truth)
    """
    id: str
    question: str
    expected_doc_ids: List[str]


# --- Segédfüggvények ---

def load_test_cases(path: str) -> List[RagTestCase]:
    """
    Tesztkérdések és elvárt doc_id-k beolvasása JSON fájlból.
    A JSON lista elemei: { "id": "...", "question": "...", "expected_doc_ids": [...] }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cases: List[RagTestCase] = []
    for item in data:
        cases.append(
            RagTestCase(
                id=item["id"],
                question=item["question"],
                expected_doc_ids=item.get("expected_doc_ids", []),
            )
        )
    return cases


def embed_text(text: str) -> List[float]:
    """
    Egyetlen szöveg embedelése OpenAI embedding modellel.
    Ugyanazt a modellt használja, mint a TypeScript backend.
    """
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text],              # egyetlen szöveg listában
        encoding_format="float",   # float32-es embedding
    )
    # OpenAI v3 embedding API: egyetlen elem van a data listában
    return resp.data[0].embedding


def search_pgvector(conn: psycopg.Connection, query: str, k: int) -> List[Dict[str, Any]]:
    """
    Ugyanaz a pgvector-alapú keresés, mint a TypeScript PgvectorVectorStore.search().
    - Embedeli a kérdést
    - SQL-ben cosine distance ( <=> ) alapján rendezi a dokumentumokat
    - TOP-K találatot ad vissza
    """
    emb = embed_text(query)

    # A pgvector a Python listát stringként várja: "[0.1,0.2,0.3,...]"
    emb_literal = "[" + ",".join(str(x) for x in emb) + "]"

    sql = """
        SELECT doc_id,
               text,
               metadata,
               1 - (embedding <=> %s::vector) AS score   -- hasonlósági pontszám
        FROM documents
        ORDER BY embedding <=> %s::vector               -- legkisebb távolság elöl
        LIMIT %s
    """

    rows = conn.execute(sql, (emb_literal, emb_literal, k)).fetchall()

    # Átalakítás Python dict listává
    results: List[Dict[str, Any]] = []
    for doc_id, text, metadata, score in rows:
        results.append(
            {
                "doc_id": doc_id,
                "text": text,
                "metadata": metadata,
                "score": float(score),
            }
        )
    return results


def precision_recall_at_k(
    expected: Set[str], retrieved: List[str], k: int
) -> Tuple[float, float]:
    """
    Egyszerű Precision@K és Recall@K számítás dokumentum ID-k alapján.
    expected: ground truth doc_id-k halmaza
    retrieved: a kereső által visszaadott doc_id-k listája
    """
    top_k = retrieved[:k]

    if not expected:
        # Ha nincs ground truth, ne torzítsa az átlagot
        return 0.0, 0.0

    # Hány találat van a top-K-ben?
    hits = sum(1 for doc_id in top_k if doc_id in expected)

    precision = hits / max(len(top_k), 1)   # találatok aránya a visszaadottak között
    recall = hits / len(expected)           # találatok aránya a ground truth-ban

    return precision, recall


# --- Fő futtatás ---

def run_rag_eval():
    """
    A teljes RAG értékelési pipeline:
    - tesztesetek beolvasása
    - embedding + pgvector keresés
    - Precision@K és Recall@K számítás
    - eredmények kiírása és JSON-be mentése
    """
    cases = load_test_cases(str(RAG_TESTS_PATH))
    print(f"Betöltött tesztesetek száma: {len(cases)}")

    total_prec = 0.0
    total_rec = 0.0
    n_with_gt = 0

    results_for_json: List[Dict[str, Any]] = []

    # PostgreSQL kapcsolat
    with psycopg.connect(PG_DSN) as conn:
        for case in cases:
            expected_set = set(case.expected_doc_ids)

            # TOP-K keresés pgvectorral
            retrieved = search_pgvector(conn, case.question, TOP_K)
            retrieved_ids = [r["doc_id"] for r in retrieved]

            # Precision@K és Recall@K
            prec, rec = precision_recall_at_k(expected_set, retrieved_ids, TOP_K)

            # Csak akkor számítjuk az átlagot, ha van ground truth
            if expected_set:
                total_prec += prec
                total_rec += rec
                n_with_gt += 1

            # Konzolra kiírás
            print(
                f"[{case.id}] P@{TOP_K}={prec:.3f}, R@{TOP_K}={rec:.3f}, "
                f"expected={list(expected_set)}, retrieved={retrieved_ids}"
            )

            # Eredmények összegyűjtése JSON-hez
            results_for_json.append(
                {
                    "id": case.id,
                    "question": case.question,
                    "expected_doc_ids": case.expected_doc_ids,
                    "retrieved": retrieved,
                    "precision_at_k": prec,
                    "recall_at_k": rec,
                }
            )

    # Átlagok számítása
    if n_with_gt > 0:
        avg_prec = total_prec / n_with_gt
        avg_rec = total_rec / n_with_gt
    else:
        avg_prec = 0.0
        avg_rec = 0.0

    summary = {
        "top_k": TOP_K,
        "num_cases": len(cases),
        "num_cases_with_ground_truth": n_with_gt,
        "avg_precision_at_k": avg_prec,
        "avg_recall_at_k": avg_rec,
    }

    print("=" * 60)
    print(f"Átlagos Precision@{TOP_K}: {avg_prec:.3f}")
    print(f"Átlagos Recall@{TOP_K}:    {avg_rec:.3f}")
    print(f"Tesztelt kérdések (GT-vel): {n_with_gt}")

    # Eredmények mentése JSON-be (pl. dolgozathoz vagy dashboardhoz)
    RAG_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAG_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": summary,
                "cases": results_for_json,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Eredmények elmentve ide: {RAG_RESULTS_PATH}")


# Ha közvetlenül futtatjuk a fájlt, induljon az értékelés
if __name__ == "__main__":
    run_rag_eval()
