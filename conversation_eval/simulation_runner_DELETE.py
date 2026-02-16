# conversation_eval/simulation_runner.py

from __future__ import annotations
import time
from typing import List
from datetime import datetime
from .assistant_client import AssistantClient
from .user_simulations import SimulatedUser 
from .types import ConversationState, Message


class SimulationRunner:
    def __init__(
        self,
        client: AssistantClient,
        user: SimulatedUser,
        session_id: str,
        max_turns: int = 6,
    ) -> None:
        self.client = client
        self.user = user
        self.session_id = session_id
        self.max_turns = max_turns

        self.state = ConversationState(
            messages=[],
            current_turn=0,
            goal_progress=0.0,
            user_satisfaction=0.0,
            frustration_level=0.0,
            context=None,
        )
        self.error_count = 0

    def run(self) -> ConversationState:
        user_input = self.user.first_message()
        self._add_message("user", user_input, latency_ms=0)

        for _ in range(self.max_turns):
            last_user_msg = self.state.messages[-1].content

            start_time = time.time()
            response = self.client.send_question(
                question=last_user_msg,
                session_id=self.session_id,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if not response.ok:
                self.error_count += 1
                self._add_message("assistant", f"[RENDSZERHIBA] {response.error}", latency_ms=latency_ms)
                break

            self._add_message("assistant", response.answer, latency_ms=latency_ms)

            next_user = self.user.next_message(self.state)
            if self.user.is_satisfied() or next_user is None:
                if next_user:
                    self._add_message("user", next_user, latency_ms=0)
                break
            self._add_message("user", next_user, latency_ms=0)

        #  A run_simulations.py innen olvassa ki a statokat!
        self.state.context = {
            "assistant_latencies_ms": [m.latency_ms for m in self.state.messages if m.role == "assistant"],
            "error_count": self.error_count
        }
        return self.state

    def _add_message(self, role: str, content: str, latency_ms: float = 0.0) -> None:
        self.state.messages.append(
            Message(
                role=role,
                content=content,
                timestamp=datetime.now(),
                turn_number=len(self.state.messages) + 1,
                latency_ms=latency_ms
            )
        )
        self.state.current_turn += 1