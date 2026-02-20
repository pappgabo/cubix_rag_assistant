# prompt_eval/run_prompt_eval.py

import json
import time
from pathlib import Path
from typing import List, Dict, Any
import time
import uuid
from monitoring.log_llm_usage import log_llm_usage
from openai import OpenAI
from dotenv import load_dotenv

from config import (
    OPENAI_API_KEY,
    PROMPT_EVAL_MODEL,
    PROMPT_EVAL_JUDGE_PROMPT_PATH,
    PROMPT_TESTS_PATH,
    PROMPT_EVAL_RESULTS_PATH,
)

# ÚJ: a saját RAG app rétegedből
from rag_app.generate_response import generate_response
from rag_app.retrieval_for_prompt_eval import retrieve_docs_for_question

# --- Inicializálás ---
load_dotenv()

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY hiányzik")

client = OpenAI(api_key=OPENAI_API_KEY)
RESULTS_PATH = PROMPT_EVAL_RESULTS_PATH


# ---------------------------------------------------------
# Tesztkérdések betöltése JSON-ből
# ---------------------------------------------------------
def load_prompt_tests(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------
# Judge rendszerprompt betöltése
# ---------------------------------------------------------
JUDGE_SYSTEM_PROMPT = PROMPT_EVAL_JUDGE_PROMPT_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------
# LLM-as-a-judge értékelés
# ---------------------------------------------------------
def judge_answer(question: str, answer: str) -> dict:
    """
    A judge modell értékeli az asszisztens válaszát.
    A judge-nek JSON formátumban kell visszaadnia az értékelést.
    """

    user_prompt = f"""
Felhasználói kérdés:
{question}

Asszisztens válasza:
{answer}

Értékeld a választ az utasításaid alapján.
Gondold át röviden, majd VÁLASZOLJ KIZÁRÓLAG az alábbi JSON objektummal, pontosan ebben a formában:

{{
  "context_relevance": ,
  "faithfulness": "",
  "answer_quality": ,
  "explanation": ""
}}
"""
    start = time.perf_counter()
    resp = client.chat.completions.create(
        model=PROMPT_EVAL_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=200,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    usage = resp.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0)
    completion_tokens = getattr(usage, "completion_tokens", 0)
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens)

    log_llm_usage({
        "requestId": str(uuid.uuid4()),
        "sessionId": None,
        "component": "prompt-judge",
        "model": PROMPT_EVAL_MODEL,
        "provider": "openai",
        "promptTokens": prompt_tokens,
        "completionTokens": completion_tokens,
        "totalTokens": total_tokens,
        "costUsd": 0.0,
        "latencyMs": latency_ms,
        "success": True,
    })

    raw = resp.choices[0].message.content

    # JSON parse hibák kezelése
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "context_relevance": 3,
            "faithfulness": "partial",
            "answer_quality": 3,
            "explanation": f"JSON parse error, raw response: {raw}",
        }


# ---------------------------------------------------------
# RAG pipeline meghívása egy kérdésre
# ---------------------------------------------------------
def call_rag_assistant(question: str) -> str:
    """
    1) Dokumentumok lekérése a baseline RAG rétegből
    2) LLM válasz generálása a visszahozott dokumentumok alapján

    Visszatérési érték:
        A generált asszisztens válasz (str)
    """

    # 1) Dokumentumok lekérése
    docs = retrieve_docs_for_question(question)

    # 2) Válasz generálása
    return generate_response(question, docs)


# ---------------------------------------------------------
# Prompt-level evaluation futtatása
# ---------------------------------------------------------
def run_prompt_eval():
    tests = load_prompt_tests(PROMPT_TESTS_PATH)
    results: List[Dict[str, Any]] = []
    total_time_ms = 0.0

    print(f"Betöltött prompt tesztek száma: {len(tests)}")

    for case in tests:
        qid = case["id"]
        question = case["question"]

        print(f"\n[{qid}] Kérdés: {question}")

        # --- 1) Válasz generálása ---
        t0 = time.perf_counter()
        answer = call_rag_assistant(question)
        t1 = time.perf_counter()

        latency_ms = (t1 - t0) * 1000

        print(f"[{qid}] Válasz (rövidítve): {answer[:120].replace('\n', ' ')}...")
        print(f"[{qid}] Latency: {latency_ms:.1f} ms")

        # --- 2) Judge értékelés ---
        judge = judge_answer(question, answer)
        print(
            f"[{qid}] Judge: "
            f"ctx_rel={judge.get('context_relevance')}, "
            f"faith={judge.get('faithfulness')}, "
            f"quality={judge.get('answer_quality')}"
        )

        total_time_ms += latency_ms

        results.append({
            "id": qid,
            "question": question,
            "answer": answer,
            "latency_ms": latency_ms,
            "judge": judge,
        })

    # ---------------------------------------------------------
    # 3) Aggregált metrikák számítása
    # ---------------------------------------------------------
    n = len(results)
    avg_latency = total_time_ms / n if n else 0.0

    avg_ctx_rel = (
        sum(r["judge"].get("context_relevance", 0) for r in results) / n if n else 0.0
    )
    avg_quality = (
        sum(r["judge"].get("answer_quality", 0) for r in results) / n if n else 0.0
    )

    faithfulness_counts = {"none": 0, "partial": 0, "strong": 0}
    for r in results:
        f = r["judge"].get("faithfulness", "none")
        if f in faithfulness_counts:
            faithfulness_counts[f] += 1

    summary = {
        "num_cases": n,
        "avg_latency_ms": avg_latency,
        "avg_context_relevance": avg_ctx_rel,
        "avg_answer_quality": avg_quality,
        "faithfulness_counts": faithfulness_counts,
    }

    # ---------------------------------------------------------
    # 4) Eredmények mentése JSON fájlba
    # ---------------------------------------------------------
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps({"summary": summary, "cases": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # 5) Összegzés kiírása
    # ---------------------------------------------------------
    print("\n" + "=" * 50)
    print("=== Prompt-level Evaluation Summary ===")
    print(f"Cases: {n}")
    print(f"Avg Latency: {avg_latency:.1f} ms")
    print(f"Avg Context Relevance: {avg_ctx_rel:.2f}/5")
    print(f"Avg Answer Quality: {avg_quality:.2f}/5")
    print(f"Faithfulness: {faithfulness_counts}")
    print(f"Results saved to: {RESULTS_PATH}")
    print("=" * 50)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
if __name__ == "__main__":
    run_prompt_eval()