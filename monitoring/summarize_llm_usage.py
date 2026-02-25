import json
import sys
import os
from collections import defaultdict

def summarize_logs(log_file="logs/llm-usage.log"):
    if not os.path.exists(log_file):
        print(f"Hiba: A log fájl nem található: {log_file}")
        return

    # Adatgyűjtők az összesítéshez
    stats = defaultdict(lambda: {
        "cost": 0.0, "p_tokens": 0, "c_tokens": 0, "count": 0, "latency": 0.0, "errors": 0
    })
    
    # Adatgyűjtők a napi bontáshoz
    daily_stats = defaultdict(lambda: defaultdict(lambda: {
        "cost": 0.0, "p_tokens": 0, "c_tokens": 0, "count": 0, "latency": 0.0, "errors": 0
    }))

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if "[LLM_USAGE]" not in line:
                    continue
                try:
                    # JSON kinyerése a log sorból
                    data = json.loads(line.split("[LLM_USAGE]")[1].strip())
                    
                    sid = data.get("sessionId") or ""
                    rid = data.get("requestId") or ""
                    comp = data.get("component") or ""
                    dt = data.get("timestamp", "")[:10] or "Ismeretlen"

                    # --- KATEGORIZÁLÁS ---
                    if sid.startswith("prod-ingest-") or sid.startswith("ingest-"):
                        cat = "SYSTEM (Ingest)"
                    elif sid.startswith("prod-") or comp == "chat":
                        cat = "PROD (User Chat)"
                    elif sid.startswith("rag-eval-"):
                        cat = "RAG-EVAL (Retrieval Test)"
                    elif sid.startswith("sim_"):
                        cat = "CONV-SIMULATION"
                    elif "judge-eval" in sid or comp == "eval-judge":
                        cat = "CONV-EVAL (Judge)"
                    elif sid.startswith("eval-run-") and rid.startswith("req-"):
                        cat = "PROMPT-EVAL (Batch Run)"
                    elif comp == "rag-embed":
                        # Beágyazások finomhangolt kezelése
                        if sid.startswith("prod-"): 
                            cat = "PROD (User Chat)"
                        elif sid.startswith("rag-eval-"): 
                            cat = "RAG-EVAL (Retrieval Test)"
                        elif sid.startswith("ingest-"): 
                            cat = "SYSTEM (Ingest)"
                        else: 
                            cat = "SYSTEM (Embeddings)"
                    else:
                        cat = f"OTHER ({comp})"

                    # Adatok rögzítése
                    for target in [daily_stats[dt][cat], stats[cat]]:
                        target["cost"] += data.get("costUsd", 0)
                        target["p_tokens"] += data.get("promptTokens", 0)
                        target["c_tokens"] += data.get("completionTokens", 0)
                        target["count"] += 1
                        target["latency"] += data.get("latencyMs", 0)
                        if not data.get("success", True):
                            target["errors"] += 1
                except:
                    continue

        # --- MEGJELENÍTÉS: DÁTUM SZERINTI BONTÁS ---
        print("\n" + "="*95)
        print(f"{'DÁTUM SZERINTI RÉSZLETES BONTÁS':^95}")
        print("="*95)
        
        for day in sorted(daily_stats.keys()):
            print(f"\n>>> NAP: {day}")
            print(f"{'KATEGÓRIA':<25} | {'DB':<4} | {'TOKEN (P/C)':<15} | {'KÖLTSÉG ($)':<12} | {'ÁTL. IDŐ'}")
            print("-" * 95)
            for cat in sorted(daily_stats[day].keys()):
                s = daily_stats[day][cat]
                avg_lat = (s["latency"] / s["count"]) / 1000 if s["count"] > 0 else 0
                tokens_str = f"{s['p_tokens']}/{s['c_tokens']}"
                print(f"{cat:<25} | {s['count']:<4} | {tokens_str:<15} | {s['cost']:<12.6f} | {avg_lat:>7.2f}s")

        # --- MEGJELENÍTÉS: VÉGLEGES ÖSSZESÍTÉS ---
        print("\n" + "="*95)
        print(f"{'VÉGLEGES ÖSSZESÍTÉS (MINDEN IDŐSZAK)':^95}")
        print("="*95)
        print(f"{'KATEGÓRIA':<25} | {'HÍVÁS':<6} | {'ÖSSZ TOKEN':<12} | {'ÖSSZ KÖLTSÉG ($)':<15} | {'ÁTL. IDŐ'}")
        print("-" * 95)
        
        grand_total_cost = 0
        grand_total_calls = 0
        
        for cat in sorted(stats.keys()):
            s = stats[cat]
            total_tokens = s["p_tokens"] + s["c_tokens"]
            # Itt volt a hiba: most már bekerült az avg_lat a printbe!
            avg_lat = (s["latency"] / s["count"]) / 1000 if s["count"] > 0 else 0
            
            grand_total_cost += s["cost"]
            grand_total_calls += s["count"]
            
            print(f"{cat:<25} | {s['count']:<6} | {total_tokens:<12} | {s['cost']:<15.6f} | {avg_lat:>8.2f}s")
            
        print("-" * 95)
        print(f"{'MINDÖSSZESEN':<25} | {grand_total_calls:<6} | {'':<12} | {grand_total_cost:<15.6f} |")
        print("="*95 + "\n")

    except Exception as e:
        print(f"Váratlan hiba történt: {e}")

if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "logs/llm-usage.log"
    summarize_logs(target_file)