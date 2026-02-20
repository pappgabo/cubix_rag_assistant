import json
from typing import Dict, Any, List
from config import PROMPT_TESTS_PATH, PROMPT_EVAL_RESULTS_PATH
from prompt_eval.test_case_loader import load_prompt_tests
from prompt_eval.eval_engine import eval_single_case, compute_summary
import time

RESULTS_PATH = PROMPT_EVAL_RESULTS_PATH


def print_case_log(case_result: Dict[str, Any]) -> None:
    qid = case_result["id"]
    question = case_result["question"]
    answer = case_result["answer"]
    latency_ms = case_result["latency_ms"]
    judge = case_result["judge"]

    print(f"\n[{qid}] Kérdés: {question}")
    print(f"[{qid}] Válasz (rövidítve): {answer[:120].replace('\\n', ' ')}...")
    print(f"[{qid}] Latency: {latency_ms:.1f} ms")
    print(
        f"[{qid}] Judge: "
        f"ctx_rel={judge.get('context_relevance')}, "
        f"faith={judge.get('faithfulness')}, "
        f"quality={judge.get('answer_quality')}"
    )


def print_summary(summary: Dict[str, Any]) -> None:
    print("\n" + "=" * 50)
    print("=== Prompt-level Evaluation Summary ===")
    print(f"Cases: {summary['num_cases']}")
    print(f"Avg Latency: {summary['avg_latency_ms']:.1f} ms")
    print(f"Avg Context Relevance: {summary['avg_context_relevance']:.2f}/5")
    print(f"Avg Answer Quality: {summary['avg_answer_quality']:.2f}/5")
    print(f"Faithfulness: {summary['faithfulness_counts']}")
    print(f"Results saved to: {RESULTS_PATH}")
    print("=" * 50)


def save_results(results: List[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps({"summary": summary, "cases": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_prompt_eval() -> None:
    # Generálunk egy SessionId-t a teljes futáshoz
    session_id = f"eval-run-{time.strftime('%Y%m%d-%H%M%S')}"
    
    tests = load_prompt_tests(PROMPT_TESTS_PATH)
    print(f"Betöltött prompt tesztek száma: {len(tests)}")

    results: List[Dict[str, Any]] = []
    for case in tests:
        case_result = eval_single_case(case, session_id=session_id)
        results.append(case_result)
        print_case_log(case_result)

    summary = compute_summary(results)
    save_results(results, summary)
    print_summary(summary)


if __name__ == "__main__":
    run_prompt_eval()
