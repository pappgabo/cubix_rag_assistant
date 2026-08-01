import os
import json
from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from config import (
    OPENAI_API_KEY,
    CONVERSATION_JUDGE_SYSTEM_PROMPT_PATH,
    CONVERSATIONS_PATH,
    JUDGE_MODEL,
    JUDGE_RESULTS_PATH,
)
from monitoring.log_llm_usage import log_llm_usage, calc_cost_usd
from utils.prompt_utils import load_prompt_file
import time
import uuid
import datetime

# config.py már meghívta a load_dotenv()-et és beolvassa a .env-et
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY nincs beállítva a .env fájlban")

# ===== OpenAI kliens =====
client = OpenAI(api_key=OPENAI_API_KEY)

JUDGE_SYSTEM_PROMPT = load_prompt_file(CONVERSATION_JUDGE_SYSTEM_PROMPT_PATH)

# ===== Helper függvények =====

def format_conversation(turns: List[Dict[str, str]]) -> str:
    """'User: ... / Bot: ...' formában fűzi össze a beszélgetést."""
    lines = []
    for t in turns:
        role = t.get("role", "")
        content = t.get("content", "")
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Bot: {content}")
        else:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def judge_conversation(
    persona: str,
    goal: str,
    turns: List[Dict[str, str]],
    session_id: str
) -> Dict[str, Any]:
    """
    Egyetlen beszélgetés értékelése LLM-mel.
    Egységes logolás, hibakezelés, költségszámítás.
    """

    conversation_text = format_conversation(turns)
    user_prompt = (
        f"Persona leírása:\n{persona}\n\n"
        f"Goal (cél):\n{goal}\n\n"
        f"Beszélgetés időrendben:\n{conversation_text}\n\n"
        "Kérlek, a fenti instrukciók szerint értékeld a beszélgetést, "
        "és CSAK a megadott JSON-formátumot add vissza."
    )

    # ---- LLM hívás + logolás ----
    start = time.perf_counter()
    request_id = str(uuid.uuid4())

    # Alapértelmezett értékek hiba esetére
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    cost_usd = 0.0
    success = False
    error_msg = None
    raw = ""

    try:
        # 1) LLM hívás
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            timeout=40.0
        )

        raw = response.choices[0].message.content.strip()

        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens

        # Egységes költségszámítás (TS oldallal megegyező)
        cost_usd = calc_cost_usd(JUDGE_MODEL, prompt_tokens, completion_tokens)

        success = True

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Judge LLM error: {error_msg}")
        success = False

    finally:
        latency_ms = int((time.perf_counter() - start) * 1000)

        # ---- Egységesített logolás ----
        try:
            log_llm_usage({
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "sessionId": session_id,
                "requestId": request_id,
                "component": "eval-judge",  
                "model": JUDGE_MODEL,
                "provider": "openai",
                "promptTokens": prompt_tokens,
                "completionTokens": completion_tokens,
                "totalTokens": total_tokens,
                "costUsd": cost_usd,
                "latencyMs": latency_ms,
                "success": success,
                "errorMessage": error_msg,  # <-- TS kompatibilis mezőnév
            })
        except Exception as log_err:
            print(f"⚠️ Logging failed in judge_conversation: {log_err}")

    # ---- JSON parse ----
    if not success:
        return {
            "goal_completion": 0,
            "answer_quality": 0,
            "explanation": f"LLM hiba történt: {error_msg}"
        }

    try:
        return json.loads(raw)

    except json.JSONDecodeError:
        # fallback: próbáljuk meg a JSON-részletet kinyerni
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            return {
                "goal_completion": 0,
                "answer_quality": 0,
                "explanation": f"Nem sikerült JSON-t parse-olni. Nyers válasz: {raw[:200]}..."
            }


def load_conversations(path: str) -> List[Dict[str, Any]]:
    """Beszélgetések betöltése JSON fájlból."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results: List[Dict[str, Any]], path: str) -> None:
    """Eredmények mentése JSON fájlba."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


# ===== Fő futtatás =====

def main():
    input_path = CONVERSATIONS_PATH
    output_path = JUDGE_RESULTS_PATH

    conversations = load_conversations(input_path)

    all_results: List[Dict[str, Any]] = []
    total_goal = 0
    total_quality = 0

    # 🔥 Egyetlen sessionId a teljes futásra
    session_id = f"judge-eval-{uuid.uuid4().hex[:6]}"

    for conv in conversations:
        conv_id = conv.get("session_id", "unknown")
        persona_id = conv.get("persona_id", "")
        goal_id = conv.get("goal_id", "")

        persona = persona_id
        goal = goal_id

        conversation_block = conv.get("conversation", {})
        turns = conversation_block.get("messages", [])

        print(f"Értékelés: {conv_id} ...")

        result = judge_conversation(
            persona,
            goal,
            turns,
            session_id=session_id
        )

        goal_score = int(result.get("goal_completion", 0))
        quality_score = int(result.get("answer_quality", 0))

        total_goal += goal_score
        total_quality += quality_score

        all_results.append({
            "id": conv_id,
            "persona_id": persona_id,
            "goal_id": goal_id,
            "scores": {
                "goal_completion": goal_score,
                "answer_quality": quality_score,
            },
            "explanation": result.get("explanation", ""),
        })

    n = len(conversations) or 1
    summary = {
        "avg_goal_completion": total_goal / n,
        "avg_answer_quality": total_quality / n,
        "num_conversations": len(conversations),
    }

    print("\nÖsszefoglaló:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    all_results.append({"summary": summary})
    save_results(all_results, str(output_path))
    print(f"\nRészletes eredmények elmentve ide: {output_path}")


if __name__ == "__main__":
    main()
