# conversation_eval/assistant_client.py

import time
import requests
from typing import Optional
from pydantic import BaseModel
from config import BACKEND_BASE_URL, CHAT_ENDPOINT

class AssistantResponse(BaseModel):
    """A backend válaszának szabványosított formátuma."""
    answer: str
    latency_ms: int
    ok: bool
    status_code: int
    error: Optional[str] = None

class AssistantClient:
    """
    Az asszisztens API-val való kommunikációért felelős kliens.
    """
    def __init__(
        self,
        base_url: str = BACKEND_BASE_URL,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    def send_question(self, question: str, session_id: str) -> AssistantResponse:
        """
        Kérdést küld a backendnek és méri a válaszidőt.
        """
        
        url = f"{self.base_url}{CHAT_ENDPOINT}"
        payload = {
            "question": question,
            "sessionId": session_id,
        }

        start_time = time.perf_counter()
        
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            # A perf_counter pontosabb ms mérésre, mint a time.time()
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                return AssistantResponse(
                    answer=data.get("answer", ""),
                    latency_ms=latency_ms,
                    ok=data.get("ok", True),
                    status_code=resp.status_code
                )
            
            return AssistantResponse(
                answer="",
                latency_ms=latency_ms,
                ok=False,
                status_code=resp.status_code,
                error=f"Server error: {resp.status_code}"
            )

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return AssistantResponse(
                answer="",
                latency_ms=latency_ms,
                ok=False,
                status_code=0,
                error=str(e)
            )

# Tesztelhetőség megőrizve
if __name__ == "__main__":
    client = AssistantClient()
    print("Kliens tesztelése...")
    res = client.send_question("Szia, ki vagy te?", "test-session-123")
    print(f"Válasz: {res.answer} ({res.latency_ms}ms)")