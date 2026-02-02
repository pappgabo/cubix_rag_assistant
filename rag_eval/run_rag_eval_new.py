from config import DOCUMENTS_CHUNKS_TABLE, DOCUMENTS_BASELINE_TABLE
from rag_eval.reranker import rerank_chunks
from rag_eval.metrics import (
    precision_recall_at_k,
    hit_at_k,
    mrr_at_k,
    f1_at_k,
    eval_case,
)
from rag_eval.retrieval import (
    load_test_cases,
    retrieve_baseline_or_chunked,
    retrieve_chunked_rerank,
)
from config import RAG_TESTS_PATH, RAG_RESULTS_PATH, RAG_TOP_K, PG_DSN

import json
import psycopg


def run_rag_eval_new():
    """
    A teljes RAG-eval pipeline futtatása:
        - baseline retrieval
        - chunked retrieval
        - chunked + CrossEncoder reranking

    Minden pipeline-ra kiszámítja:
        - precision@k
        - recall@k
        - hit@k
        - mrr@k
        - f1@k

    Az eredményeket JSON-ba menti.
    """

    # ------------------------------------------------------------
    # 1) Tesztesetek betöltése
    # ------------------------------------------------------------
    cases = load_test_cases(str(RAG_TESTS_PATH))
    print(f"Betöltött tesztesetek száma: {len(cases)}")

    all_results = {}

    # PostgreSQL kapcsolat
    with psycopg.connect(PG_DSN) as conn:

        # ------------------------------------------------------------
        # 2) BASELINE és CHUNKED PIPELINE ÉRTÉKELÉSE
        # ------------------------------------------------------------
        for pipeline_name in [DOCUMENTS_BASELINE_TABLE, DOCUMENTS_CHUNKS_TABLE]:
            print(f"\n=== Pipeline futtatása: {pipeline_name} ===")

            # Összegző változók (átlagoláshoz)
            total_prec = total_rec = total_hit = total_mrr = total_f1 = 0.0
            n_with_gt = 0
            pipeline_results = []

            # ------------------------------------------------------------
            # 2/A) Minden teszteset lefuttatása
            # ------------------------------------------------------------
            for case in cases:

                # baseline/chunked retrieval → (raw találatok, egyedi base_id lista)
                raw, retrieved_ids = retrieve_baseline_or_chunked(
                    conn=conn,
                    table_name=pipeline_name,
                    question=case.question,
                    top_k=RAG_TOP_K,
                )

                # metrikák kiszámítása (precision, recall, hit, mrr, f1)
                metrics = eval_case(
                    expected_ids=set(case.expected_doc_ids),
                    retrieved_ids=retrieved_ids,
                    top_k=RAG_TOP_K
                )

                # metrikák kibontása
                prec = metrics["precision_at_k"]
                rec = metrics["recall_at_k"]
                hit = metrics["hit_at_k"]
                mrr = metrics["mrr_at_k"]
                f1 = metrics["f1_at_k"]

                # csak akkor számítjuk bele az átlagba, ha van ground truth
                if case.expected_doc_ids:
                    total_prec += prec
                    total_rec += rec
                    total_hit += hit
                    total_mrr += mrr
                    total_f1 += f1
                    n_with_gt += 1

                # logolás
                print(
                    f"[{pipeline_name}][{case.id}] "
                    f"P@{RAG_TOP_K}={prec:.3f}, R@{RAG_TOP_K}={rec:.3f}, "
                    f"retrieved={retrieved_ids}"
                )

                # eredmények eltárolása JSON-hoz
                pipeline_results.append(
                    {
                        "id": case.id,
                        "question": case.question,
                        "expected_doc_ids": case.expected_doc_ids,
                        "retrieved": metrics["retrieved_raw"],
                        **metrics,
                    }
                )

            # ------------------------------------------------------------
            # 2/B) Átlag metrikák kiszámítása
            # ------------------------------------------------------------
            if n_with_gt:
                avg_prec = total_prec / n_with_gt
                avg_rec = total_rec / n_with_gt
                avg_hit = total_hit / n_with_gt
                avg_mrr = total_mrr / n_with_gt
                avg_f1 = total_f1 / n_with_gt
            else:
                avg_prec = avg_rec = avg_hit = avg_mrr = avg_f1 = 0.0

            # pipeline összegzése
            all_results[pipeline_name] = {
                "summary": {
                    "top_k": RAG_TOP_K,
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
        # 3) CHUNKED + RERANK PIPELINE (CrossEncoder)
        # ------------------------------------------------------------
        print("\n=== Pipeline futtatása: chunked_rerank ===")

        total_prec = total_rec = total_hit = total_mrr = total_f1 = 0.0
        n_with_gt = 0
        pipeline_results = []

        for case in cases:

            # chunked retrieval + CrossEncoder reranking
            _, _, retrieved_ids = retrieve_chunked_rerank(
                conn=conn,
                question=case.question,
                table_name=DOCUMENTS_CHUNKS_TABLE,
                top_k=RAG_TOP_K,
                candidate_k=RAG_TOP_K * 4,  # több jelölt → jobb reranking
                rerank_fn=rerank_chunks,
            )

            metrics = eval_case(
                expected_ids=set(case.expected_doc_ids),
                retrieved_ids=retrieved_ids,
                top_k=RAG_TOP_K
            )

            prec = metrics["precision_at_k"]
            rec = metrics["recall_at_k"]
            hit = metrics["hit_at_k"]
            mrr = metrics["mrr_at_k"]
            f1 = metrics["f1_at_k"]

            if case.expected_doc_ids:
                total_prec += prec
                total_rec += rec
                total_hit += hit
                total_mrr += mrr
                total_f1 += f1
                n_with_gt += 1

            print(
                f"[chunked_rerank][{case.id}] "
                f"P@{RAG_TOP_K}={prec:.3f}, R@{RAG_TOP_K}={rec:.3f}, "
                f"retrieved={retrieved_ids}"
            )

            pipeline_results.append(
                {
                    "id": case.id,
                    "question": case.question,
                    "expected_doc_ids": case.expected_doc_ids,
                    "retrieved": metrics["retrieved_raw"],
                    **metrics,
                }
            )

        # átlag metrikák
        if n_with_gt:
            avg_prec = total_prec / n_with_gt
            avg_rec = total_rec / n_with_gt
            avg_hit = total_hit / n_with_gt
            avg_mrr = total_mrr / n_with_gt
            avg_f1 = total_f1 / n_with_gt
        else:
            avg_prec = avg_rec = avg_hit = avg_mrr = avg_f1 = 0.0

        all_results["chunked_rerank"] = {
            "summary": {
                "top_k": RAG_TOP_K,
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
    # 4) Eredmények mentése JSON-ba
    # ------------------------------------------------------------
    RAG_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAG_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\nEredmények elmentve ide: {RAG_RESULTS_PATH}")


if __name__ == "__main__":
    run_rag_eval_new()
