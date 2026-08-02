# Ez a modul felelős egy teljes batch szimuláció lefuttatásáért.
# A batch futás célja: több persona × több goal kombinációt végigfuttatni
# és minden beszélgetést elmenteni egy JSON fájlba.
#
# A tesztesetek NINCSENEK beégetve a kódba — a YAML konfigurációból jönnek.
# A YAML útvonalát a config.py tartalmazza (BATCH_CONFIG_PATH),
# így a QA / regression testing teljesen konfigurálható.

import json
import yaml
from pathlib import Path
from datetime import datetime

# Globális konfigurációk
from config import (
    BACKEND_BASE_URL,
    OPENAI_API_KEY,
    CONVERSATIONS_PATH,
    BATCH_CONFIG_PATH,
)

# Szimulációs komponensek
from conversation_eval.assistant_client import AssistantClient
from conversation_eval.simulated_user_llm import SimulatedUserLLM
from conversation_eval.orchestration import ConversationOrchestrator
# Előre definiált personák és célok
from conversation_eval.personas import PREDEFINED_PERSONAS
from conversation_eval.goals import PREDEFINED_GOALS


# ---------------------------------------------------------------------------
# YAML KONFIGURÁCIÓ BETÖLTÉSE
# ---------------------------------------------------------------------------
def load_batch_config(path=None):
    """
    Betölti a batch futáshoz szükséges YAML konfigurációt.

    A path paraméter opcionális:
    - ha nincs megadva, a config.py-ban definiált BATCH_CONFIG_PATH-et használjuk.
    - így a batch runner NEM tartalmaz beégetett útvonalakat.
    """
    config_path = path or BATCH_CONFIG_PATH

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# BATCH FUTTATÁSA
# ---------------------------------------------------------------------------
def run_batch():
    """
    A teljes batch szimuláció futtatása.

    Lépések:
    1. YAML konfiguráció betöltése (personák + goalok listája)
    2. Szimulációs mátrix lefuttatása (persona x goal)
    3. Eredmények mentése JSON-be
    """
    print(f"🚀 Batch Runner indítása (Backend: {BACKEND_BASE_URL})")

    # 1) YAML konfiguráció betöltése
    cfg = load_batch_config()
    test_personas = cfg["personas"]
    test_goals = cfg["goals"]

    # Asszisztens API kliens
    client = AssistantClient(base_url=BACKEND_BASE_URL)

    # Ide gyűjtjük a futások eredményeit
    batch_results = []

    # -----------------------------------------------------------------------
    # 2) SZIMULÁCIÓS MÁTRIX (persona × goal)
    # -----------------------------------------------------------------------
    for p_id in test_personas:
        for g_id in test_goals:

            # Persona és goal objektumok betöltése
            persona = PREDEFINED_PERSONAS[p_id]
            goal = PREDEFINED_GOALS[g_id]

            # Egyedi session ID minden futáshoz
            session_id = f"sim_{p_id}_{g_id}_{datetime.now().strftime('%m%d_%H%M')}"

            print(f"🎬 Futás: {persona.name} + {goal.id}...")

            # Szimulált user (LLM-alapú)
            user = SimulatedUserLLM(OPENAI_API_KEY, persona, goal)

            # Orchestrator: a beszélgetés teljes folyamatát vezérli
            orchestrator = ConversationOrchestrator(client, user, session_id)

            # A beszélgetés lefuttatása
            final_state = orchestrator.run()


            # Eredmény rögzítése
            batch_results.append({
                "session_id": session_id,
                "persona_id": p_id,
                "goal_id": g_id,
                # A 'mode="json"' paraméter biztosítja, hogy a datetime-ból string legyen!
                "conversation": final_state.model_dump(mode="json"), # Pydantic → dict
                "timestamp": datetime.now().isoformat()
            })

    # -----------------------------------------------------------------------
    # 3) EREDMÉNYEK MENTÉSE
    # -----------------------------------------------------------------------
    Path(CONVERSATIONS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CONVERSATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(batch_results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Batch kész! Eredmények itt: {CONVERSATIONS_PATH}")


# ---------------------------------------------------------------------------
# FŐPROGRAM
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_batch()
