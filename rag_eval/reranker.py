# reranker.py
from typing import List, Dict
from config import RERANKER_MODEL
from sentence_transformers import CrossEncoder


# A CrossEncoder egy olyan modell, amely NEM embeddingeket ad vissza,
# hanem közvetlenül pontozza a (query, chunk) párokat.
# Ez sokkal pontosabb, mint a cosine similarity, mert a két szöveget együtt olvassa,
# és figyelembe veszi a kontextust, a jelentést, a kapcsolódást.
reranker_model = CrossEncoder(RERANKER_MODEL)


def rerank_chunks(
    query: str,
    chunks: List[Dict],
    top_n: int,
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

    # 1. Query–chunk párok létrehozása.
    # A modell így tudja megítélni, mennyire releváns egy chunk a kérdéshez.
    pairs = [[query, c["text"]] for c in chunks]

    # 2. A modell minden párra ad egy pontszámot (float).
    # Minél magasabb, annál relevánsabb a chunk.
    scores = reranker_model.predict(pairs)

    # 3. A pontszámokat visszaírjuk a chunkok mellé.
    for c, s in zip(chunks, scores):
        c["rerank_score"] = float(s)

    # 4. A chunkokat a relevancia pontszám alapján rendezzük (csökkenő sorrend).
    reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

    # 5. Visszaadjuk a legjobb top_n chunkot.
    return reranked[:top_n]
