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

# A logok könyvtára a projekt futtatási helyéhez képest
LOGS_DIR = Path(os.getcwd()) / "logs"

# A konkrét logfájl útvonala
LOG_FILE = LOGS_DIR / "llm-usage.log"


def log_llm_usage(entry: dict) -> None:
    """
    Egy LLM-hívás metaadatait (latency, költség, komponens stb.)
    kiírja a logfájlba.

    A bejegyzés formátuma:
        [LLM_USAGE] {"component": "...", "latencyMs": ..., "costUsd": ...}

    - Ha nincs timestamp, automatikusan hozzáadjuk (UTC ISO formátumban).
    - A logfájl és a könyvtár automatikusan létrejön, ha nem létezik.
    """

    # Gondoskodunk róla, hogy a logs/ könyvtár létezzen
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Ha nincs timestamp, generálunk egyet
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.utcnow().isoformat() + "Z"

    # A log sor formátuma: prefix + JSON
    line = f"[LLM_USAGE] {json.dumps(entry, ensure_ascii=False)}\n"

    # Hozzáfűzés a logfájlhoz
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)
