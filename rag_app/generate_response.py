
import time, uuid 
from datetime import datetime, timezone
from typing import List
from openai import OpenAI
from utils.prompt_utils import load_prompt_file

# Központi konfiguráció és monitoring
from config import OPENAI_API_KEY, PROMPT_EVAL_MODEL, PROJECT_ROOT
from monitoring.log_llm_usage import log_llm_usage, calc_cost_usd

# 1. Definiáljuk a prompt fájlok útvonalát
RAG_SYSTEM_PROMPT_PATH = PROJECT_ROOT / "rag_app" / "rag_system_prompt.txt" #ezt maj ki kell vinni config.py-ba
RAG_USER_PROMPT_PATH = PROJECT_ROOT / "rag_app" / "rag_user_prompt.txt" #ezt maj ki kell vinni config.py-ba


def generate_response(
    query: str, 
    documents: List[str], 
    session_id: str = None,
    request_id: str = None
) -> str:
    """
    RAG válaszgenerálás: külső promptok, egységes logolás és precíz költségszámítás.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY hiányzik a konfigurációból.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Mérés indítása és azonosítók
    start = time.perf_counter()
    r_id = request_id or str(uuid.uuid4())
    s_id = session_id or f"gen-fallback-{uuid.uuid4().hex[:6]}"
    
    # Alapértékek a logoláshoz
    prompt_tokens = 0
    completion_tokens = 0
    cost_usd = 0.0
    success = False
    error_msg = None
    final_text = ""

    try:
        # 2. PROMPTOK BEOLVASÁSA ÉS FORMÁZÁSA
        # A fájlokban CSAK a nyers szöveg van (nincs változónév vagy idézőjel)
        system_message = load_prompt_file(RAG_SYSTEM_PROMPT_PATH)
        user_template = load_prompt_file(RAG_USER_PROMPT_PATH)

        formatted_docs = "\n\n".join(
            f"Dokumentum {i+1}:\n{doc}"
            for i, doc in enumerate(documents)
        )

        # A .txt fájlból jövő {query} és {documents} helyek kitöltése
        user_message = user_template.format(
            query=query,
            documents=formatted_docs
        )

        # 3. LLM HÍVÁS
        resp = client.chat.completions.create(
            model=PROMPT_EVAL_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=400,
            temperature=0.2,
            timeout=30.0
        )
        
        final_text = resp.choices[0].message.content
        prompt_tokens = resp.usage.prompt_tokens
        completion_tokens = resp.usage.completion_tokens
        
        # 4. KÖLTSÉGSZÁMÍTÁS (8 tizedesjegy)
        cost_usd = calc_cost_usd(PROMPT_EVAL_MODEL, prompt_tokens, completion_tokens)
        success = True

    except Exception as e:
        success = False
        error_msg = str(e)
        final_text = f"Hiba a generálás során: {error_msg}"
        print(f"❌ RAG Response Error: {error_msg}")

    finally:
        # 5. EGYSÉGES NAPLÓZÁS
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        # A modernebb datetime használata a hiba elkerülésére
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        log_llm_usage({
            "timestamp": timestamp,
            "sessionId": s_id,
            "requestId": r_id,
            "component": "rag-response",
            "model": PROMPT_EVAL_MODEL,
            "provider": "openai",
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "totalTokens": prompt_tokens + completion_tokens,
            "costUsd": cost_usd,
            "latencyMs": latency_ms,
            "success": success,
            "errorMessage": error_msg
        })

    return final_text