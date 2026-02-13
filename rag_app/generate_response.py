# rag_app/generate_response.py

import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """
Te egy segítőkész recept-asszisztens vagy.
A feladatod, hogy a megadott receptek (kontextus) alapján válaszolj a felhasználó kérdésére.

Szabályok:
- Csak a megadott receptekből dolgozz!
- Ha a válasz nincs benne a kontextusban, mondd azt:
  "Sajnos erről nincs információm a recepttáramban."
- Légy barátságos, de tömör, ne ismételd feleslegesen önmagad.
"""

USER_PROMPT = """
Kérdés: {query}

Kontextus (receptek részletei):
{documents}

Válaszolj magyarul, a fenti szabályok szerint.
"""

def generate_response(query: str, documents: List[str]) -> str:
    """
    Egyszerű RAG válaszgenerálás:
    - query: felhasználói kérdés
    - documents: releváns dokumentum-szövegek listája
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY hiányzik")

    client = OpenAI(api_key=api_key)

    # Kontextus összefűzése
    formatted_documents = "\n\n".join(
        f"Dokumentum {i+1}:\n{doc}"
        for i, doc in enumerate(documents)
    )

    user_message = USER_PROMPT.format(
        query=query,
        documents=formatted_documents,
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",  # vagy amit 3.2-re használsz
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=400,
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Hiba a generálás során: {str(e)}"