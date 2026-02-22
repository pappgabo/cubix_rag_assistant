import time, uuid
from config import PROMPT_TESTS_PATH
from utils.load_prompt_test import load_prompt_test
from prompt_eval.prompt_judge import judge_answer
from rag_app.generate_response import generate_response
from rag_app.retrieval_for_prompt_eval import retrieve_docs_for_question
from typing import List, Dict, Any

def call_rag_assistant(question: str, session_id: str, request_id: str) -> str:
    docs = retrieve_docs_for_question(question, session_id=session_id, request_id=request_id)
    # A generate_response-nak is át KELL adni, különben újat generál magának!
    return generate_response(
        question, 
        docs, 
        session_id=session_id, 
        request_id=request_id
    )

def eval_single_case(case: Dict[str, Any],session_id: str) -> Dict[str, Any]:
    qid = case["id"]
    question = case["question"]
    # Ez lesz a közös RequestId a RAG és a Judge számára!
    # Így egy q1 kérdéshez tartozó beágyazás és bíráskodás azonos lesz.
    request_id = f"req-{qid}-{uuid.uuid4().hex[:8]}"

    t0 = time.perf_counter()
    # Továbbpasszoljuk mindkét hívásnak
    answer = call_rag_assistant(question, session_id=session_id, request_id=request_id)
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000

    judge = judge_answer(
        question, 
        answer, 
        session_id=session_id, 
        request_id=request_id
    )

    return {
        "id": qid,
        "request_id": request_id,
        "question": question,
        "answer": answer,
        "latency_ms": latency_ms,
        "judge": judge,
    }


def run_all_cases() -> List[Dict[str, Any]]:
    tests = load_prompt_test(PROMPT_TESTS_PATH)
    return [eval_single_case(case) for case in tests]


def compute_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(results)
    if n == 0:
        return {
            "num_cases": 0,
            "avg_latency_ms": 0.0,
            "avg_context_relevance": 0.0,
            "avg_answer_quality": 0.0,
            "faithfulness_counts": {"none": 0, "partial": 0, "strong": 0},
        }

    total_time_ms = sum(r["latency_ms"] for r in results)
    avg_latency = total_time_ms / n
    avg_ctx_rel = sum(r["judge"].get("context_relevance", 0) for r in results) / n
    avg_quality = sum(r["judge"].get("answer_quality", 0) for r in results) / n

    faithfulness_counts = {"none": 0, "partial": 0, "strong": 0}
    for r in results:
        f = r["judge"].get("faithfulness", "none")
        if f in faithfulness_counts:
            faithfulness_counts[f] += 1

    return {
        "num_cases": n,
        "avg_latency_ms": avg_latency,
        "avg_context_relevance": avg_ctx_rel,
        "avg_answer_quality": avg_quality,
        "faithfulness_counts": faithfulness_counts,
    }
