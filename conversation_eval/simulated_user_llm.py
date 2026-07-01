# conversation_eval/simulated_user_llm.py

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from openai import OpenAI

from config import SIMULATED_USER_MODEL, SIMULATED_USER_SYSTEM_PROMPT_PATH
from monitoring.log_llm_usage import log_llm_usage, calc_cost_usd
from utils.prompt_utils import load_prompt_file

from .types import ConversationGoal, ConversationState, UserPersona


class SimulatedUserLLM:
    """LLM-alapú szimulált felhasználó egységes logolással."""

    def __init__(
        self,
        openai_api_key: str,
        persona: UserPersona,
        goal: ConversationGoal,
        session_id: str = "sim-fallback",
    ) -> None:
        self.client = OpenAI(api_key=openai_api_key)
        self.persona = persona
        self.goal = goal
        self.satisfied = False
        self.session_id = session_id
        self._system_template = load_prompt_file(SIMULATED_USER_SYSTEM_PROMPT_PATH)

    def _build_system_prompt(self) -> str:
        return self._system_template.format(
            persona_description=self.persona.description,
            persona_patience=self.persona.patience,
            persona_expertise=self.persona.expertise,
            persona_clarity=self.persona.clarity_of_communication,
            goal_description=self.goal.description,
        )

    def _call_llm(self, messages, component: str) -> Optional[str]:
        start = time.perf_counter()
        request_id = str(uuid.uuid4())
        prompt_tokens = 0
        completion_tokens = 0
        cost_usd = 0.0
        success = False
        content = None
        error_msg = None

        try:
            resp = self.client.chat.completions.create(
                model=SIMULATED_USER_MODEL,
                messages=messages,
                timeout=30.0,
            )
            content = resp.choices[0].message.content
            prompt_tokens = resp.usage.prompt_tokens
            completion_tokens = resp.usage.completion_tokens
            cost_usd = calc_cost_usd(
                SIMULATED_USER_MODEL, prompt_tokens, completion_tokens
            )
            success = True
        except Exception as e:
            error_msg = str(e)
            print(f"❌ LLM Error [{component}]: {error_msg}")

        latency_ms = int((time.perf_counter() - start) * 1000)
        log_llm_usage(
            {
                "timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "requestId": request_id,
                "sessionId": self.session_id,
                "component": component,
                "model": SIMULATED_USER_MODEL,
                "provider": "openai",
                "promptTokens": prompt_tokens,
                "completionTokens": completion_tokens,
                "totalTokens": prompt_tokens + completion_tokens,
                "costUsd": cost_usd,
                "latencyMs": latency_ms,
                "success": success,
                "errorMessage": error_msg,
            }
        )
        return content

    def first_message(self) -> str:
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {
                "role": "user",
                "content": (
                    f"Kezdd el a beszélgetést a célod érdekében: {self.goal.description}"
                ),
            },
        ]
        return self._call_llm(messages, component="simulated-user-first") or ""

    def next_message(self, state: ConversationState) -> Optional[str]:
        history = []
        for message in state.messages:
            role_label = (
                "YOUR PREVIOUS MESSAGE"
                if message.role == "user"
                else "ASSISTANT RESPONSE"
            )
            history.append(
                {
                    "role": message.role,
                    "content": f"[{role_label}]: {message.content}",
                }
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            *history,
        ]
        content = self._call_llm(messages, component="simulated-user-next")

        stop_words = ["viszlát", "köszönöm", "szia", "rendben vagyunk"]
        if content and any(word in content.lower() for word in stop_words):
            self.satisfied = True

        return content

    def is_satisfied(self) -> bool:
        return self.satisfied
