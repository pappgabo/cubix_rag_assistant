# scripts/summarize_llm_usage.py
#
# Ez a script az LLM-hívások naplófájljából (log) összegyűjti a
# [LLM_USAGE] jelöléssel ellátott sorokat, majd statisztikát készít:
# - összes hívás száma
# - összköltség USD-ben
# - átlagos és p95 latency
# - komponensenkénti bontás (pl. RAG, chat, memory, judge)
#
# A log formátuma tipikusan így néz ki:
#   [2025-01-01 12:00:00] [LLM_USAGE] {"component": "rag", "latencyMs": 123, "costUsd": 0.00045}
#
# A script futtatása:
#   python scripts/summarize_llm_usage.py logs/llm-usage.log

import json
import sys
from pathlib import Path
from statistics import mean


# ---------------------------------------------------------------------------
# LOGFÁJL BEOLVASÁSA
# ---------------------------------------------------------------------------
def read_log_file(path: str):
    """
    Beolvassa a logfájlt, és kinyeri belőle a [LLM_USAGE] sorok JSON tartalmát.

    Működés:
    - soronként olvas
    - csak azokat a sorokat vizsgálja, amelyek tartalmazzák a "[LLM_USAGE]" jelölést
    - a jelölés utáni JSON részt megpróbálja parse-olni
    - hibás JSON esetén a sort kihagyja
    """
    entries = []
    text = Path(path).read_text(encoding="utf-8")

    for line in text.splitlines():
        # Csak az LLM_USAGE sorok érdekesek
        if "[LLM_USAGE]" not in line:
            continue

        # A jelölés utáni JSON rész kivágása
        json_part = line.split("[LLM_USAGE]", 1)[1].strip()
        if not json_part:
            continue

        # JSON parse
        try:
            entry = json.loads(json_part)
            entries.append(entry)
        except json.JSONDecodeError:
            # Ha a JSON hibás, egyszerűen átugorjuk
            continue

    return entries


# ---------------------------------------------------------------------------
# STATISZTIKÁK KÉSZÍTÉSE
# ---------------------------------------------------------------------------
def summarize(entries):
    """
    Kiírja az LLM-hívások összesített statisztikáit.

    Tartalmazza:
    - összes hívás számát
    - összköltséget USD-ben
    - átlagos latency-t
    - p95 latency-t
    - komponensenkénti bontást
    """
    if not entries:
        print("Nincs LLM_USAGE log bejegyzés.")
        return

    # Összköltség
    total_cost = sum(e.get("costUsd", 0) for e in entries)

    # Latency statisztikák
    latencies = [e.get("latencyMs", 0) for e in entries]
    latencies_sorted = sorted(latencies)
    avg_latency = mean(latencies_sorted)
    p95_idx = int(len(latencies_sorted) * 0.95)
    p95_latency = latencies_sorted[p95_idx] if latencies_sorted else 0

    print("=== LLM Usage Summary ===")
    print(f"Összes hívás: {len(entries)}")
    print(f"Összes költség (USD): {total_cost:.6f}")
    print(f"Átlag latency (ms): {avg_latency:.2f}, p95 latency (ms): {p95_latency}")

    # Komponensenkénti bontás (pl. rag, chat, judge)
    by_component = {}
    for e in entries:
        comp = e.get("component", "unknown")
        bucket = by_component.setdefault(
            comp, {"count": 0, "cost": 0.0, "latencies": []}
        )
        bucket["count"] += 1
        bucket["cost"] += e.get("costUsd", 0)
        bucket["latencies"].append(e.get("latencyMs", 0))

    print("\nKomponensenként:")
    for comp, stats in by_component.items():
        avg_comp_lat = mean(stats["latencies"]) if stats["latencies"] else 0
        print(
            f"  - {comp}: count={stats['count']}, "
            f"cost={stats['cost']:.6f} USD, "
            f"avgLatency={avg_comp_lat:.2f} ms"
        )


# ---------------------------------------------------------------------------
# FŐPROGRAM
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Ellenőrizzük, hogy megadtak-e logfájlt
    if len(sys.argv) < 2:
        print("Használat: python scripts/summarize_llm_usage.py logs/llm-usage.log")
        sys.exit(1)

    log_file = sys.argv[1]

    # Log beolvasása és összegzés
    entries = read_log_file(log_file)
    summarize(entries)
