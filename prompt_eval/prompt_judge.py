import json
import time
import uuid
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from config import OPENAI_API_KEY, PROMPT_EVAL_MODEL, PROMPT_EVAL_JUDGE_PROMPT_PATH,GPT41_MINI_IN_PER_M, GPT41_MINI_OUT_PER_M
from monitoring.log_llm_usage import log_llm_usage

load_dotenv()
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY hiányzik")

client = OpenAI(api_key=OPENAI_API_KEY)
# A prompt betöltése külső fájlból
JUDGE_SYSTEM_PROMPT = PROMPT_EVAL_JUDGE_PROMPT_PATH.read_text(encoding="utf-8")

def judge_answer(question: str, answer: str, session_id: str, request_id: str) -> Dict[str, Any]:
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
    # --- Mérés indítása ---
    start = time.perf_counter()
    #run_id = str(uuid.uuid4())
    #session_id = f"prompt-eval-{run_id}"

    session_id = session_id or f"judge-fallback-{uuid.uuid4().hex[:6]}"
    run_id = request_id or f"req-gen-{uuid.uuid4().hex[:6]}"
    
    resp = client.chat.completions.create(
        model=PROMPT_EVAL_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=400, # Megemeltem kicsit az explanation miatt
    )
    
    # --- Token használat kinyerése ---
    prompt_tokens = resp.usage.prompt_tokens
    completion_tokens = resp.usage.completion_tokens
    total_tokens = resp.usage.total_tokens

    cost_usd = (prompt_tokens * GPT41_MINI_IN_PER_M / 1_000_000 + 
                completion_tokens * GPT41_MINI_OUT_PER_M / 1_000_000)

    latency_ms = int((time.perf_counter() - start) * 1000)

    # --- Token használat kinyerése ---
    #usage = resp.usage
    #prompt_tokens = getattr(usage, "prompt_tokens", 0)
    #completion_tokens = getattr(usage, "completion_tokens", 0)
    #total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens)

    # --- Logolás ---
    log_llm_usage({
        "requestId": request_id,   # Kapott ID használata UUID.uuid4() helyett
        "sessionId": session_id,   # A teljes futás azonosítója
        "component": "prompt-judge",
        "model": PROMPT_EVAL_MODEL,
        "provider": "openai",
        "promptTokens": prompt_tokens,
        "completionTokens": completion_tokens,
        "totalTokens": total_tokens,
        "costUsd": cost_usd,
        "latencyMs": latency_ms,
        "success": True,
    })

    # --- Válasz feldolgozása ---
    raw = resp.choices[0].message.content
    try:
        # Tisztítás, ha az LLM véletlenül ```json ... ``` közé tenné
        cleaned_raw = raw.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_raw)
    except json.JSONDecodeError:
        return {
            "context_relevance": 1,
            "faithfulness": "none",
            "answer_quality": 1,
            "explanation": f"Bírói hiba: Nem sikerült feldolgozni a választ. Raw: {raw}",
        }
