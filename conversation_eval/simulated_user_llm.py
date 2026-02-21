# conversation_eval/simulated_user_llm.py

from typing import Optional
from openai import OpenAI
from .types import UserPersona, ConversationGoal, ConversationState
from config import SIMULATED_USER_MODEL, GPT41_MINI_IN_PER_M, GPT41_MINI_OUT_PER_M
from monitoring.log_llm_usage import log_llm_usage
import time
import uuid


class SimulatedUserLLM:
    """
    LLM-alapú szimulált felhasználó, részletes LLM-usage logolással.
    """

    def __init__(self, openai_api_key: str, persona: UserPersona, goal: ConversationGoal, session_id: str = "sim-fallback"):
        self.client = OpenAI(api_key=openai_api_key)
        self.persona = persona
        self.goal = goal
        self.satisfied = False
        self.session_id = session_id


    # ------------------------------------------------------------
    # SYSTEM PROMPT
    # ------------------------------------------------------------
    def _build_system_prompt(self) -> str:
        return f"""
        Te egy szimulált felhasználó vagy egy beszélgetésben. NEM vagy mesterséges intelligencia, NEM chatbot és NEM asszisztens.

        SZEMÉLYISÉG (Persona): {self.persona.description}

        JELLEMZŐK:
        - Türelem: {self.persona.patience}
        - Szakértelem: {self.persona.expertise}
        - Világosság: {self.persona.clarity_of_communication}

        A CÉLOD:
        {self.goal.description}

        SZABÁLYOK:
        1. SOHA ne ajánlj fel segítséget.
        2. Te vagy az, akinek szüksége van valamire.
        3. Ha az asszisztens kérdez valamit, válaszolj a személyiséged alapján.
        4. Ha az asszisztens nem segítőkész, légy frusztrált vagy ismételd meg a kérésedet.
        5. Beszélj ELSŐ SZEMÉLYBEN.
        """


    # ------------------------------------------------------------
    # EGYSÉGES LLM-HÍVÁS LOGOLÁSSAL
    # ------------------------------------------------------------
    def _call_llm(self, messages, component: str) -> Optional[str]:
        """
        Egységes LLM-hívás hibakezeléssel és garantált logolással.
        """
        start = time.perf_counter()
        request_id = str(uuid.uuid4())

        # Alapértelmezett értékek hiba esetére
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        cost_usd = 0.0
        success = False
        content = None
        error_msg = None

        try:
            # 1) LLM hívás
            resp = self.client.chat.completions.create(
                model=SIMULATED_USER_MODEL,
                messages=messages,
                timeout=30.0
            )

            content = resp.choices[0].message.content
            usage = resp.usage

            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            cost_usd = (
                prompt_tokens * GPT41_MINI_IN_PER_M / 1_000_000 +
                completion_tokens * GPT41_MINI_OUT_PER_M / 1_000_000
            )

            success = True

        except Exception as e:
            error_msg = str(e)
            print(f"❌ LLM Error [{component}]: {error_msg}")
            success = False

        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)

            # 2) Logolás (külön try-ban)
            try:
                log_llm_usage({
                    "requestId": request_id,
                    "sessionId": self.session_id,
                    "component": component,
                    "model": SIMULATED_USER_MODEL,
                    "provider": "openai",
                    "promptTokens": prompt_tokens,
                    "completionTokens": completion_tokens,
                    "totalTokens": total_tokens,
                    "costUsd": cost_usd,
                    "latencyMs": latency_ms,
                    "success": success,
                    "error": error_msg,
                })
            except Exception as log_err:
                print(f"⚠️ Critical: Logging failed! {log_err}")

        return content


    # ------------------------------------------------------------
    # KEZDŐ ÜZENET
    # ------------------------------------------------------------
    def first_message(self) -> str:
        messages = [
            {'role': 'system', 'content': self._build_system_prompt()},
            {
                'role': 'user',
                'content': f"Kezdd el a beszélgetést a célod érdekében: {self.goal.description}"
            },
        ]

        return self._call_llm(messages, component="simulated-user-first")


    # ------------------------------------------------------------
    # KÖVETKEZŐ ÜZENET
    # ------------------------------------------------------------
    def next_message(self, state: ConversationState) -> Optional[str]:
        history = []
        for m in state.messages:
            role_label = "YOUR PREVIOUS MESSAGE" if m.role == "user" else "ASSISTANT RESPONSE"
            history.append({"role": m.role, "content": f"[{role_label}]: {m.content}"})

        messages = [
            {'role': 'system', 'content': self._build_system_prompt()},
            *history
        ]

        content = self._call_llm(messages, component="simulated-user-next")

        # egyszerű lezárási logika
        stop_words = ["viszlát", "köszönöm", "szia", "rendben vagyunk"]
        if content and any(word in content.lower() for word in stop_words):
            self.satisfied = True

        return content


    # ------------------------------------------------------------
    # ÁLLAPOT
    # ------------------------------------------------------------
    def is_satisfied(self) -> bool:
        return self.satisfied
