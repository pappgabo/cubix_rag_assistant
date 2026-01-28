# scripts/summarize_llm_usage.py
import json
import sys
from pathlib import Path
from statistics import mean

def read_log_file(path: str):
    entries = []
    text = Path(path).read_text(encoding="utf-8")
    for line in text.splitlines():
        if "[LLM_USAGE]" not in line:
            continue
        json_part = line.split("[LLM_USAGE]", 1)[1].strip()
        if not json_part:
            continue
        try:
            entry = json.loads(json_part)
            entries.append(entry)
        except json.JSONDecodeError:
            continue
    return entries

def summarize(entries):
    if not entries:
        print("Nincs LLM_USAGE log bejegyzés.")
        return

    total_cost = sum(e.get("costUsd", 0) for e in entries)
    latencies = [e.get("latencyMs", 0) for e in entries]
    latencies_sorted = sorted(latencies)
    avg_latency = mean(latencies_sorted)
    p95_idx = int(len(latencies_sorted) * 0.95)
    p95_latency = latencies_sorted[p95_idx] if latencies_sorted else 0

    print("=== LLM Usage Summary ===")
    print(f"Összes hívás: {len(entries)}")
    print(f"Összes költség (USD): {total_cost:.6f}")
    print(f"Átlag latency (ms): {avg_latency:.2f}, p95 latency (ms): {p95_latency}")

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Használat: python scripts/summarize_llm_usage.py logs/llm-usage.log")
        sys.exit(1)

    log_file = sys.argv[1]
    entries = read_log_file(log_file)
    summarize(entries)