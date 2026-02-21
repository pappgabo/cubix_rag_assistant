# smoke_test.py
import os
from dotenv import load_dotenv
from conversation_eval.assistant_client import AssistantClient
from conversation_eval.simulated_user_llm_old import SimulatedUserLLM
from conversation_eval.orchestration import ConversationOrchestrator
from conversation_eval.types import UserPersona, ConversationGoal

# Környezeti változók betöltése (OPENAI_API_KEY)
load_dotenv()

def run_test():
    print("🚀 Teszt indítása...")

    # 1. Setup: Persona és Cél
    test_persona = UserPersona(
        id="test-p", name="Teszt Elek", 
        description="Egy kedves, de nagyon tömör felhasználó.",
        patience=0.9, expertise=0.5, verbosity=0.2, 
        frustration_tolerance=0.8, clarity_of_communication=0.9, technical_level=0.5
    )
    
    test_goal = ConversationGoal(
        id="test-g", 
        description="Szeretnék egy pörkölt receptet kérni.",
        success_criteria=["Megkapja a receptet"],
        expected_turns=3, domain="general", complexity="simple"
    )

    # 2. Komponensek inicializálása
    client = AssistantClient(base_url="http://localhost:3000") # Ellenőrizd a portot!
    user = SimulatedUserLLM(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        persona=test_persona,
        goal=test_goal
    )
    
    orchestrator = ConversationOrchestrator(
        client=client,
        user=user,
        session_id="smoke-test-session"
    )

    # 3. Futtatás
    print("💬 Beszélgetés folyamatban...")
    final_state = orchestrator.run()

    # 4. Kiértékelés (Konzolra)
    print("\n--- EREDMÉNY ---")
    for msg in final_state.messages:
        latency = f"({msg.latency_ms}ms)" if msg.role == "assistant" else ""
        print(f"[{msg.role.upper()}] {latency}: {msg.content[:100]}...")

    print(f"\nÖsszes kör: {final_state.current_turn}")
    print(f"Hibák száma: {final_state.context.get('error_count')}")

if __name__ == "__main__":
    run_test()