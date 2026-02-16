# conversation_eval/simulated_user.py

from __future__ import annotations
from typing import Optional
from .types import UserPersona, ConversationGoal, ConversationState


class SimulatedUser:
    """
    A szimulált felhasználó domain-entitása.

    Felelőssége:
    - A persona + goal alapján üzeneteket generálni.
    - Az asszisztens válaszára reagálni (recept felismerése, pontosítás kérése).
    - Jelezni, ha a cél teljesült (satisfied=True).

    Fontos:
    - NEM tartja számon a köröket (turns).
    - NEM dönti el, mikor ér véget a beszélgetés technikai értelemben.
    Ezek a SimulationRunner felelősségei.
    """

    # Kulcsszavak, amelyek alapján eldöntjük, hogy receptet kaptunk-e
    # (Heurisztikus megközelítés az LLM-hívások megspórolására)
    RECIPE_KEYWORDS = ["hozzávalók", "elkészítés", "lépés", "sütés", "főzés", "gramm", "perc", "adag"]

    # Kulcsszavak negatív asszisztens válasz felismeréséhez (pl. ha nincs találat a RAG-ban)
    NEGATIVE_KEYWORDS = ["sajnos", "nem találok", "nincs a gyűjteményben", "sajnálom", "nem sikerült"]

    def __init__(self, persona: UserPersona, goal: ConversationGoal) -> None:
        """
        Inicializálás a persona (stílus) és a goal (cél) alapján.
        """
        self.persona = persona
        self.goal = goal
        self.satisfied = False  # Ezt a flaget fogja a SimulationRunner figyelni

    # ----------------------------------------------------------------------
    # PUBLIC API - Ezt hívja a SimulationRunner
    # ----------------------------------------------------------------------

    def first_message(self) -> str:
        """
        A beszélgetés indító üzenete.
        A persona alapvető stílusát és a konkrét célt kombinálja.
        """
        base = f"Szia! {self.goal.description} kapcsán keresek segítséget."
        return self._apply_persona_tone(base)

    def next_message(self, state: ConversationState) -> Optional[str]:
        """
        A szimulátor döntési logikája az asszisztens utolsó válasza alapján.
        Ha None-t ad vissza, az a beszélgetés megszakítását jelenti.
        """
        if not state.messages:
            return None

        # Az asszisztens legutolsó válaszának elemzése
        last_msg = str(state.messages[-1].content or "").lower()

        # 1. eset: Az asszisztens megadta a receptet (vagy annak tűnő választ)
        if self._found_recipe(last_msg):
            return self._handle_recipe_found()

        # 2. eset: Az asszisztens jelezte, hogy nem tud segíteni
        if self._is_negative(last_msg):
            return self._apply_persona_tone(
                "Értem. Esetleg valami hasonló receptet tudnál ajánlani a gyűjteményedből?"
            )

        # 3. eset: Általános válasz / Visszakérdezés az asszisztenstől
        # Ilyenkor a user türelmesen (vagy a stílusának megfelelően) újra kéri a célt.
        followup = (
            f"Ez érdekesen hangzik, de tudnál konkrétan a '{self.goal.description}' "
            "kapcsán egy pontos receptet vagy leírást adni?"
        )
        return self._apply_persona_tone(followup)

    def is_satisfied(self) -> bool:
        """
        A SimulationRunner ezzel ellenőrizheti, hogy a cél teljesült-e.
        Visszatérési érték: True, ha a user megkapta a receptet.
        """
        return self.satisfied

    # ----------------------------------------------------------------------
    # PRIVATE LOGIKA - Belső segédfüggvények
    # ----------------------------------------------------------------------

    def _apply_persona_tone(self, message: str) -> str:
        """
        Ráhúzza a persona stílusát az alap üzenetre.
        Ez teszi lehetővé, hogy ugyanaz a cél másként hangozzon a chaten.
        """
        # Nagyon beszédes / Precíz persona
        if self.persona.verbosity > 0.7:
            return (
                message 
                + f" Mivel {self.persona.description}, kérlek, hogy nagyon alaposan, "
                  "minden apró részletre kiterjedően válaszolj."
            )

        # Tömör / Sietős persona
        if self.persona.verbosity < 0.3:
            # Rövidítünk és kivesszük az udvariaskodást
            minimal = message.replace("érdekesen hangzik, de", "oké.").replace("kapcsán keresek segítséget", "kellene")
            return f"Röviden: {minimal}"

        # Normál stílus
        return message

    def _found_recipe(self, msg: str) -> bool:
        """
        Heurisztika: eldönti, hogy a válasz tartalmaz-e receptre utaló jeleket.
        Legalább 2 kulcsszó jelenléte esetén tekintjük receptnek.
        """
        found_count = sum(1 for kw in self.RECIPE_KEYWORDS if kw in msg)
        return found_count >= 2

    def _is_negative(self, msg: str) -> bool:
        """Eldönti, hogy az asszisztens elutasító választ adott-e (pl. nincs találat)."""
        return any(kw in msg for kw in self.NEGATIVE_KEYWORDS)

    def _handle_recipe_found(self) -> str:
        """
        Amikor a szimulátor úgy érzékeli, megvan a recept.
        Beállítja az állapotot és generál egy lezáró üzenetet.
        """
        self.satisfied = True
        return self._apply_persona_tone(
            "Köszönöm szépen, ez pont az, amit kerestem! El is mentem a receptet, sokat segítettél."
        )