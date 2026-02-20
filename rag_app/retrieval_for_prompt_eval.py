# rag_app/retrieval_for_prompt_eval.py

from typing import List
import psycopg

from config import PG_DSN, RAG_TOP_K
from rag_eval.retrieval import retrieve_baseline_or_chunked


def retrieve_docs_for_question(question: str, top_k: int | None = None, session_id: str | None = None,  # Új paraméter
    request_id: str | None = None ) -> List[str]:
    """
    Baseline RAG retrieval egy kérdéshez.

    Feladata:
    - megnyit egy PostgreSQL kapcsolatot (PG_DSN)
    - meghívja a retrieve_baseline_or_chunked függvényt a documents_baseline táblára
    - a visszakapott raw találatokból összegyűjti a 'text' mezőket
    - ezeket List[str] formában visszaadja

    Ezt használja a prompt-szintű eval (3.2) kontextus építéshez.
    """

    # Ha nincs megadva top_k → használjuk a globális RAG_TOP_K értéket
    if top_k is None:
        top_k = RAG_TOP_K

    texts: List[str] = []

    # Ugyanaz a PG_DSN, mint a 3.1-es RAG evalban
    with psycopg.connect(PG_DSN) as conn:

        # A retrieve_baseline_or_chunked két értéket ad vissza:
        #   raw_results: a teljes sorok (dict-ek)
        #   retrieved_ids: a base_id-k listája (itt nem kell)
        raw_results, _retrieved_ids = retrieve_baseline_or_chunked(
            conn=conn,
            table_name="documents_baseline",
            question=question,
            top_k=top_k,
            session_id=session_id, # Továbbpasszolás
            request_id=request_id  # Továbbpasszolás
        )

        # A raw_results tipikusan így néz ki:
        # [
        #   {"doc_id": "...", "base_id": "...", "text": "...", "metadata": {...}, "score": ...},
        #   ...
        # ]
        for row in raw_results:
            if isinstance(row, dict):
                text = row.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text)

    return texts
