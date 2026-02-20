# conversation_eval/orchestrator.py

from __future__ import annotations
import time
from typing import List
from datetime import datetime
from .assistant_client import AssistantClient
from .user_simulations import SimulatedUser 
from .types import ConversationState, Message


class ConversationOrchestrator:
    """
    A beszélgetés teljes folyamatát vezérlő komponens.

    Felelőssége:
    - A user → assistant → user ciklus koordinálása.
    - A turn-limit betartatása (végtelen ciklusok ellen).
    - Latency mérése és rögzítése.
    - Hibák kezelése (pl. asszisztens nem válaszol).
    - A beszélgetés állapotának (ConversationState) folyamatos frissítése.
    """

    def __init__(
        self,
        client: AssistantClient,
        user: SimulatedUser,
        session_id: str,
        max_turns: int = 6,
    ) -> None:
        # Az asszisztens API-kliense
        self.client = client

        # A szimulált felhasználó (viselkedési logika)
        self.user = user

        # Session ID — fontos a backend oldali kontextushoz
        self.session_id = session_id

        # Végtelen ciklusok ellen: maximum ennyi kör lehet
        self.max_turns = max_turns

        # A beszélgetés állapota (üzenetek, turn-szám, metaadatok)
        self.state = ConversationState(
            messages=[],
            current_turn=0,
            goal_progress=0.0,
            user_satisfaction=0.0,
            frustration_level=0.0,
            context=None,
        )

        # Hány asszisztens-hiba történt (pl. API error)
        self.error_count = 0

    def run(self) -> ConversationState:
        """
        Levezényel egy teljes beszélgetést az elejétől a végéig.
        Visszaadja a ConversationState-et, amely tartalmazza az összes üzenetet
        és a metaadatokat (latency, hibák száma stb.).
        """

        # 1) A szimulált user első üzenete
        user_input = self.user.first_message()
        self._add_message("user", user_input, latency_ms=0)

        # 2) A beszélgetés fő ciklusa
        for _ in range(self.max_turns):

            # A user legutóbbi üzenete → erre válaszol az asszisztens
            last_user_msg = self.state.messages[-1].content

            # --- Asszisztens hívása + latency mérése ---
            start_time = time.time()
            response = self.client.send_question(
                question=last_user_msg,
                session_id=self.session_id,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            # Ha az asszisztens hibát dobott → logoljuk és leállunk
            if not response.ok:
                self.error_count += 1
                error_msg = f"[RENDSZERHIBA] Az asszisztens nem válaszolt: {response.error}"
                self._add_message("assistant", error_msg, latency_ms=latency_ms)
                break

            # Asszisztens válaszának rögzítése
            self._add_message("assistant", response.answer, latency_ms=latency_ms)

            # --- User válasza az asszisztens üzenetére ---
            next_user_text = self.user.next_message(self.state)

            # Ha a user elégedett lett vagy nincs több mondanivalója → vége
            # FONTOS: a satisfied flag a next_message() belsejében frissül
            if self.user.is_satisfied() or next_user_text is None:
                # Ha még küld egy utolsó üzenetet (pl. "Köszönöm"), azt rögzítjük
                if next_user_text:
                    self._add_message("user", next_user_text, latency_ms=0)
                break

            # Normál eset: a user folytatja a beszélgetést
            self._add_message("user", next_user_text, latency_ms=0)

        # --- Beszélgetés lezárása: statisztikák rögzítése ---
        self.state.context = {
            # Asszisztens válaszidejei (ms)
            "assistant_latencies_ms": [
                m.latency_ms for m in self.state.messages if m.role == "assistant"
            ],
            # Hány API-hiba történt
            "error_count": self.error_count
        }

        return self.state

    def _add_message(self, role: str, content: str, latency_ms: int = 0) -> None:
        """
        Segédmetódus a Message objektumok konzisztens létrehozásához.
        Minden üzenet:
        - kap timestampet,
        - kap turn-számot,
        - kap latency-t (ha asszisztens válasz),
        - bekerül a ConversationState-be.
        """
        self.state.messages.append(
            Message(
                role=role,
                content=content,
                timestamp=datetime.now(),
                turn_number=len(self.state.messages) + 1,
                latency_ms=latency_ms
            )
        )

        # A ConversationState-ben vezetjük a turn-számot
        self.state.current_turn += 1
