# reranker.py
from typing import List, Dict
from config import RERANKER_MODEL
from sentence_transformers import CrossEncoder
from monitoring.log_llm_usage import log_llm_usage
import uuid, time
from datetime import datetime, timezone


# A CrossEncoder egy olyan modell, amely NEM embeddingeket ad vissza,
# hanem közvetlenül pontozza a (query, chunk) párokat.
# Ez sokkal pontosabb, mint a cosine similarity, mert a két szöveget együtt olvassa,
# és figyelembe veszi a kontextust, a jelentést, a kapcsolódást.
reranker_model = CrossEncoder(RERANKER_MODEL)

def rerank_chunks(
    query: str,
    chunks: List[Dict],
    top_n: int,
    session_id: str = None,
    request_id: str = None,
) -> List[Dict]:
    """
    A pgvector által visszaadott találatokat (chunks) újrarendezi egy CrossEncoder segítségével.

    Paraméterek:
        query:   a felhasználó kérdése (string)
        chunks:  a pgvector top-K találatai, mindegyik egy dict:
                 {
                     "text": "...",
                     "base_id": "...",
                     "metadata": {...},
                     "score": <cosine similarity>
                 }
        top_n:   hány elemet adjon vissza a reranking után
                 (általában 5, de a RAG evalban lehet dinamikus)

    Működés:
        1. A query és minden chunk szövegéből párokat készítünk.
        2. A CrossEncoder minden párra ad egy relevancia pontszámot.
        3. A chunkokhoz hozzárendeljük ezeket a pontszámokat.
        4. A chunkokat a pontszám alapján sorba rendezzük.
        5. Visszaadjuk a legjobb top_n chunkot.
    """

    # Ha nincs mit rerankelni, térjünk vissza üres listával.
    if not chunks:
        return []

    # 1. Időmérés indítása
    start = time.perf_counter()
    success = True
    error_msg = None
    reranked = []

    try:
        # 2. Relevancia pontozás
        pairs = [[query, c["text"]] for c in chunks]
        scores = reranker_model.predict(pairs)

        for c, s in zip(chunks, scores):
            c["rerank_score"] = float(s)

        # 3. Rendezés
        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

    except Exception as e:
        success = False
        error_msg = str(e)
        print(f"❌ Reranker error: {error_msg}")
        

    finally:
        # 4. Látencia számítása és logolás
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        log_llm_usage({
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sessionId": session_id,
            "requestId": request_id or str(uuid.uuid4()),
            "component": "rag-rerank",
            "model": RERANKER_MODEL,
            "provider": "local",
            "promptTokens": 0,
            "completionTokens": 0,
            "totalTokens": 0,
            "costUsd": 0.0,
            "latencyMs": latency_ms,
            "success": success,
            "errorMessage": error_msg
        })

    return reranked[:top_n]
