# conversation_eval/simulated_user_llm.py

from typing import Optional
from openai import OpenAI
from .types import UserPersona, ConversationGoal, ConversationState, Message
from config import SIMULATED_USER_MODEL


class SimulatedUserLLM:
    """
    Egy LLM-alapú szimulált felhasználó.
    
    Ez a verzió NEM heurisztikákat használ (mint a SimulatedUser),
    hanem egy külön OpenAI-modellt kér meg arra, hogy a felhasználó
    szerepét játssza el a beszélgetésben.

    Fő előnye:
    - sokkal életszerűbb, változatosabb válaszok
    - a persona finomabb árnyalatai is megjelennek
    - a cél (goal) alapján dinamikusan reagál

    Hátránya:
    - lassabb és drágább, mint a heurisztikus user
    """

    def __init__(self, openai_api_key: str, persona: UserPersona, goal: ConversationGoal):
        # OpenAI kliens inicializálása
        self.client = OpenAI(api_key=openai_api_key)

        # A szimulált user személyisége és célja
        self.persona = persona
        self.goal = goal

        # A SimulationOrchestrator ezt figyeli majd
        self.satisfied = False

    # ----------------------------------------------------------------------
    # SYSTEM PROMPT — a modellnek elmagyarázzuk, hogyan viselkedjen
    # ----------------------------------------------------------------------
    def _build_system_prompt(self) -> str:
        """
        A rendszerüzenet, amely meghatározza a szimulált felhasználó
        személyiségét, célját és viselkedési szabályait.
        """
        return f"""
        Te egy szimulált felhasználó vagy egy beszélgetésben. NEM vagy mesterséges intelligencia, NEM chatbot és NEM asszisztens.

        SZEMÉLYISÉG (Persona): {self.persona.description}

        JELLEMZŐK:
        - Türelem: {self.persona.patience} (0=türelmetlen, 1=nagyon nyugodt)
        - Szakértelem: {self.persona.expertise} (0=kezdő, 1=profi)
        - Világosság: {self.persona.clarity_of_communication} (0=zagyva, 1=érthető)

        A CÉLOD:
        {self.goal.description}

        SZABÁLYOK:
	    1. SOHA ne ajánlj fel segítséget. SOHA ne kérdezd meg, hogy "Miben segíthetek?".
	    2. Te vagy az, akinek szüksége van valamire.
	    3. Ha az asszisztens kérdez valamit, a személyiséged alapján válaszolj.
	    4. Ha az asszisztens nem segítőkész, légy frusztrált, vagy ismételd meg a kérésedet a türelmednek megfelelően.
	    5. Beszélj ELSŐ SZEMÉLYBEN (pl. "Azt akarom...", "Kereselek...").
        """


    # ----------------------------------------------------------------------
    # KEZDŐ ÜZENET
    # ----------------------------------------------------------------------
    def first_message(self) -> str:
        """
        A beszélgetés indítása.
        A rendszerprompt + egy user prompt alapján az LLM generálja
        a szimulált felhasználó első üzenetét.
        """
        response = self.client.chat.completions.create(
            model=SIMULATED_USER_MODEL,
            messages=[
                {'role': 'system', 'content': self._build_system_prompt()},
                {
                    'role': 'user',
                    'content': f"Kezdd el a beszélgetést a célod érdekében: {self.goal.description}"
                },
            ]
        )

        # Az LLM által generált első üzenet
        return response.choices[0].message.content

    # ----------------------------------------------------------------------
    # KÖVETKEZŐ ÜZENET — a teljes beszélgetési előzmény alapján
    # ----------------------------------------------------------------------
    def next_message(self, state: ConversationState) -> Optional[str]:
        """
        A szimulált felhasználó válasza az asszisztens üzenetére.
        A teljes beszélgetési előzményt elküldjük az LLM-nek,
        így kontextusban tud reagálni.
        """

        # A beszélgetés előzménye OpenAI formátumban
        history = []
        for m in state.messages:
            # Explicit emlékeztető a modellnek, hogy melyik üzenet kié
            role_label = "YOUR PREVIOUS MESSAGE" if m.role == "user" else "ASSISTANT RESPONSE"
            history.append({"role": m.role, "content": f"[{role_label}]: {m.content}"})

        # LLM hívás a teljes kontextussal
        response = self.client.chat.completions.create(
            model=SIMULATED_USER_MODEL,
            messages=[
                {'role': 'system', 'content': self._build_system_prompt()},
                *history
            ]
        )

        content = response.choices[0].message.content

        # Egyszerű lezárási logika:
        # Ha a user elköszön vagy jelzi, hogy elégedett → satisfied=True
        stop_words = ["viszlát", "köszönöm", "szia", "rendben vagyunk"]
        if any(word in content.lower() for word in stop_words):
            self.satisfied = True

        return content

    # ----------------------------------------------------------------------
    # ÁLLAPOT LEKÉRDEZÉSE
    # ----------------------------------------------------------------------
    def is_satisfied(self) -> bool:
        """
        A SimulationOrchestrator ezzel ellenőrzi,
        hogy a szimulált user elérte-e a célját.
        """
        return self.satisfied
