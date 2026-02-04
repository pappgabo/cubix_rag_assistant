from typing import List, Set, Tuple, Dict, Any


def precision_recall_at_k(
    expected: Set[str],
    retrieved: List[str],
    k: int
) -> Tuple[float, float]:
    """
    Precision@K és Recall@K kiszámítása.
    expected: a helyes (ground truth) base_id-k halmaza
    retrieved: a rendszer által visszaadott base_id-k listája
    """
    top_k = retrieved[:k]

    if not expected:
        return 0.0, 0.0

    hits = sum(1 for doc_id in top_k if doc_id in expected)

    precision = hits / max(len(top_k), 1)
    recall = hits / len(expected)

    return precision, recall


def hit_at_k(expected: Set[str], retrieved: List[str], k: int) -> float:
    """
    Hit@K: 1, ha a helyes dokumentum benne van a top-K listában, különben 0.
    """
    if not expected:
        return 0.0

    top_k = retrieved[:k]
    return 1.0 if any(doc_id in expected for doc_id in top_k) else 0.0


def mrr_at_k(expected: Set[str], retrieved: List[str], k: int) -> float:
    """
    MRR@K: Reciprocal Rank — ha a helyes dokumentum a rank pozíción van,
    akkor 1/rank, ha nincs a top-K-ben, akkor 0.
    """
    if not expected:
        return 0.0

    for rank, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in expected:
            return 1.0 / rank

    return 0.0


def unique_base_ids_in_order(
    retrieved: List[Dict[str, Any]],
    k: int
) -> List[str]:
    """
    A chunkokból kiszedi a base_id-ket, sorrendben, duplikációk nélkül.
    Ez azért kell, mert több chunk tartozhat ugyanahhoz a dokumentumhoz.
    """
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


def f1_at_k(precision: float, recall: float) -> float:
    """
    F1-score: a precision és recall harmonikus átlaga.
    """
    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)

def eval_case(
    expected_ids: Set[str],
    retrieved_ids: List[str],
    top_k: int,
) -> Dict[str, Any]: 
    prec, rec = precision_recall_at_k(expected_ids, retrieved_ids, top_k)
    hit = hit_at_k(expected_ids, retrieved_ids, top_k)
    mrr = mrr_at_k(expected_ids, retrieved_ids, top_k)
    f1 = f1_at_k(prec, rec)
    top_ids = retrieved_ids[:top_k]

    return {
        "precision_at_k": prec,   # 'precision' helyett, hogy a fő script megtalálja
        "recall_at_k": rec,      # 'recall' helyett
        "hit_at_k": hit,         # 'hit' helyett
        "mrr_at_k": mrr,         # 'mrr' helyett
        "f1_at_k": f1,           # 'f1' helyett
        "retrieved_ids": top_ids, 
    }