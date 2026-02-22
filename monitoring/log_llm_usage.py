# monitoring/log_llm_usage.py
#
# Ez a modul felelős azért, hogy minden LLM-hívásról
# egységes formátumú logbejegyzés készüljön.
#
# A logok a /logs/llm-usage.log fájlba kerülnek,
# minden sor egy JSON objektumot tartalmaz, amelyet
# a [LLM_USAGE] prefix jelöl. Ezeket később a
# summarize_llm_usage.py tudja feldolgozni.

import json
import os
from datetime import datetime
from pathlib import Path
from collections import OrderedDict

LOGS_DIR = Path(os.getcwd()) / "logs"
LOG_FILE = LOGS_DIR / "llm-usage.log"

# Egységes árlista a TS oldallal
MODEL_PRICES = {
    "gpt-4.1-mini": {"input": 0.00015, "output": 0.0006},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
}

def calc_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prices = MODEL_PRICES.get(model)
    if not prices: return 0.0
    cost = (prompt_tokens / 1000) * prices["input"] + (completion_tokens / 1000) * prices["output"]
    return float(f"{cost:.8f}") # Kényszerített 8 tizedes

def log_llm_usage(entry: dict) -> None:
    # 1. Időbélyeg pótlása, ha hiányzik
    ts = entry.get("timestamp") or (datetime.utcnow().isoformat() + "Z")

    # 2. OrderedDict használata a FIX sorrendért
    ordered = OrderedDict([
        ("timestamp", ts),
        ("sessionId", entry.get("sessionId")),
        ("requestId", entry.get("requestId")),
        ("component", entry.get("component")),
        ("model", entry.get("model")),
        ("provider", entry.get("provider", "openai")),
        ("promptTokens", entry.get("promptTokens", 0)),
        ("completionTokens", entry.get("completionTokens", 0)),
        ("totalTokens", entry.get("totalTokens", 0)),
        ("costUsd", entry.get("costUsd", 0.0)),
        ("latencyMs", entry.get("latencyMs", 0)),
        ("success", entry.get("success", True)),
        ("errorMessage", entry.get("errorMessage"))
    ])

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # JAVÍTOTT json.dumps: az 'ordered' objektumot szerializáljuk!
    line = f"[LLM_USAGE] {json.dumps(ordered, ensure_ascii=False)}\n"

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())