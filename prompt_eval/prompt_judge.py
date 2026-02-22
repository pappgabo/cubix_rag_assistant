import json, time, uuid
from datetime import datetime, timezone 
from typing import Dict, Any
from openai import OpenAI
from config import OPENAI_API_KEY, PROMPT_EVAL_MODEL, PROMPT_EVAL_JUDGE_PROMPT_PATH, PROMPT_EVAL_JUDGE_USER_PATH
from monitoring.log_llm_usage import log_llm_usage, calc_cost_usd
from utils.prompt_utils import load_prompt_file

client = OpenAI(api_key=OPENAI_API_KEY)

def judge_answer(question: str, answer: str, session_id: str = None, request_id: str = None) -> Dict[str, Any]:
    # --- Mérés indítása ---
    start = time.perf_counter()
    s_id = session_id or f"judge-fallback-{uuid.uuid4().hex[:6]}"
    r_id = request_id or str(uuid.uuid4())
    
    # --- Promptok betöltése az util-lal ---
    system_prompt = load_prompt_file(PROMPT_EVAL_JUDGE_PROMPT_PATH)
    user_template = load_prompt_file(PROMPT_EVAL_JUDGE_USER_PATH)

    # Behelyettesítés a sablonba (a fájlban csak a nyers szöveg van!)
    user_prompt = user_template.format(question=question, answer=answer)
    print(user_prompt) #ezt csekkolás miatt

    try:
        resp = client.chat.completions.create(
            model=PROMPT_EVAL_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_completion_tokens=500,
        )
        
        # --- Adatok kinyerése ---
        prompt_tokens = resp.usage.prompt_tokens
        completion_tokens = resp.usage.completion_tokens
        cost_usd = calc_cost_usd(PROMPT_EVAL_MODEL, prompt_tokens, completion_tokens)
        
        # --- Logolás (Konzisztens a rerankerrel és generálással) ---
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_llm_usage({
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sessionId": s_id,
            "requestId": r_id,
            "component": "prompt-judge",
            "model": PROMPT_EVAL_MODEL,
            "provider": "openai",
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "totalTokens": prompt_tokens + completion_tokens,
            "costUsd": cost_usd,
            "latencyMs": latency_ms,
            "success": True,
        })

        # --- Válasz feldolgozása ---
        raw = resp.choices[0].message.content
        cleaned_raw = raw.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_raw)

    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_llm_usage({
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sessionId": s_id,
            "requestId": r_id,
            "component": "prompt-judge",
            "model": PROMPT_EVAL_MODEL,
            "success": False,
            "errorMessage": str(e),
            "latencyMs": latency_ms
        })