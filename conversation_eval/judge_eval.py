import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from config import OPENAI_API_KEY, JUDGE_MODEL, CONVERSATIONS_PATH, JUDGE_RESULTS_PATH, GPT41_MINI_IN_PER_M, GPT41_MINI_OUT_PER_M
from monitoring.log_llm_usage import log_llm_usage
import time
import uuid
#config.py már meghívta a load_dotenv()-et és beolvassa a .env-et

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY nincs beállítva a .env fájlban")

# ===== OpenAI kliens =====

client = OpenAI(api_key=OPENAI_API_KEY)

# ===== System prompt a judge-hoz =====

JUDGE_SYSTEM_PROMPT = """
Te egy független értékelő vagy, aki többkörös (multi-turn) receptajánló beszélgetéseket értékel.

Feladatod:
- A TELJES beszélgetést nézd (összes kör, user + bot üzenetek).
- Vedd figyelembe a persona leírását és a goal-t (célfeladatot).
- 0-3 skálán értékeld:
  1) goal_completion: a beszélgetés végére a felhasználó reálisan eljutott-e egy neki megfelelő, elkészíthető megoldásig;
  2) answer_quality: mennyire helyesek, relevánsak és használhatóak a bot válaszai összességében a beszélgetés során.

Skála:
- 0 = teljes kudarc
  - goal_completion: a beszélgetés végén nincs használható recept / megoldás, vagy a bot teljesen félremegy (pl. allergiát figyelmen kívül hagy, korpuszon kívüli dolgokat talál ki).
  - answer_quality: a válaszok többnyire hibásak, irrelevánsak vagy nagyon zavarosak.
- 1 = gyenge
  - goal_completion: valamennyire közelebb jut, de a felhasználó számára nem igazán alkalmazható a javaslat (pl. hiányzó hozzávalókra nem reagál, időkorlátot nem tartja).
  - answer_quality: vegyes minőség, több pontatlanság vagy irreleváns rész; a felhasználónak sokat kellene improvizálnia.
- 2 = jó
  - goal_completion: a beszélgetés végére kap a felhasználó egy alapvetően használható receptet vagy megoldást, ami illeszkedik a personához és a goal-hoz, kisebb hiányosságokkal.
  - answer_quality: a válaszok többnyire helyesek és relevánsak, a fontos korlátokat (idő, alapanyag, allergén) többnyire betartja, a lépések nagyjából követhetőek.
- 3 = kiváló
  - goal_completion: a beszélgetés világosan elvezet egy jól definiált, reálisan elkészíthető recepthez / megoldáshoz, amely teljesen megfelel a persona céljainak és korlátainak.
  - answer_quality: a válaszok végig pontosak, relevánsak, nincsenek ellentmondások, a bot következetesen emlékszik az előző körökre (pl. allergénekre, eszközökre, időkeretre), és a lépések érthetőek.

Fontos:
- Ha a korpuszban nincs desszert, de a felhasználó desszertet kér, magasabb pont jár azért, ha a bot NEM talál ki desszert receptet, hanem korrekt fallbacket ad (korpuszkorlát jelzése, alternatíva javaslata).
- Mindig a TELJES beszélgetés alapján dönts, ne csak az első válasz alapján.
- A persona stílusát is vedd figyelembe: pl. türelmetlen kezdőnek érték, ha a bot rövid és lépésről lépésre magyaráz; haladó gasztrofanatikusnál fontosabbak a technikai részletek.

Kimenet:
Mindig CSAK a következő JSON-t add vissza, további magyarázó szöveg nélkül:

{
  "goal_completion": 0-3 egész szám,
  "answer_quality": 0-3 egész szám,
  "explanation": "rövid, 2-4 mondatos indoklás magyarul, konkrét hivatkozásokkal a beszélgetés kulcsmomentumaival"
}
"""

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


def judge_conversation(persona: str, goal: str, turns: List[Dict[str, str]]) -> Dict[str, Any]:
    
    conversation_text = format_conversation(turns)
    user_prompt = (
        f"Persona leírása:\n{persona}\n\n"
        f"Goal (cél):\n{goal}\n\n"
        f"Beszélgetés időrendben:\n{conversation_text}\n\n"
        "Kérlek, a fenti instrukciók szerint értékeld a beszélgetést, "
        "és CSAK a megadott JSON-formátumot add vissza."
    )
    start = time.perf_counter()
    run_id = str(uuid.uuid4())
    session_id = f"rag-eval-{run_id}"


    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens

    cost_usd = (prompt_tokens * GPT41_MINI_IN_PER_M / 1_000_000 + 
                completion_tokens * GPT41_MINI_OUT_PER_M / 1_000_000)

    latency_ms = int((time.perf_counter() - start) * 1000)

    

    log_llm_usage(
        {
            "requestId": str(uuid.uuid4()),
            "sessionId": None,          # vagy conv_id, ha átadod paraméterként
            "component": "judge",
            "model": JUDGE_MODEL,
            "provider": "openai",
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "totalTokens": total_tokens,
            "costUsd": cost_usd,            # ha akarod, később itt is számolhatsz
            "latencyMs": latency_ms,
            "success": True,
        }
    )

    raw = response.choices[0].message.content.strip()

    # JSON parse, minimális hibakezeléssel
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # fallback: próbáljuk meg a JSON-részletet kinyerni
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            result = json.loads(raw[start:end])
        except Exception:
            result = {
                "goal_completion": 0,
                "answer_quality": 0,
                "explanation": f"Nem sikerült a JSON-t parse-olni. Nyers válasz: {raw[:200]}..."
            }
    return result



def load_conversations(path: str) -> List[Dict[str, Any]]:
    """Beszélgetések betöltése JSON fájlból."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results: List[Dict[str, Any]], path: str) -> None:
    """Eredmények mentése JSON fájlba."""
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

    for conv in conversations:
        # ÚJ: az új JSON-struktúrához igazítva
        conv_id = conv.get("session_id", "unknown")
        persona_id = conv.get("persona_id", "")
        goal_id = conv.get("goal_id", "")

        # Ha van külön persona/goal leíró szöveg, itt tudod beolvasni,
        # de most használhatod simán az ID-kat is:
        persona = persona_id
        goal = goal_id

        conversation_block = conv.get("conversation", {})
        # Itt a messages lista már {role, content, ...} formában van
        turns = conversation_block.get("messages", [])

        print(f"Értékelés: {conv_id} ...")

        result = judge_conversation(persona, goal, turns)
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