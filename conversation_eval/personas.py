from typing import Dict

from .types import UserPersona

PREDEFINED_PERSONAS: Dict[str, UserPersona] = {
    "impatient_chef": UserPersona(
        id="impatient-chef",
        name="Impatient Chef",
        description=(
            "Profi szakács, aki siet. Tömör, szakmai válaszokat vár, "
            "nem szereti a felesleges magyarázkodást."
        ),
        patience=0.2,
        expertise=0.9,
        verbosity=0.2,
        frustration_tolerance=0.3,
        clarity_of_communication=0.9,
        technical_level=0.9,
    ),
    "beginner_cook": UserPersona(
        id="beginner-cook",
        name="Beginner Cook",
        description=(
            "Lelkes kezdő, aki fél elrontani az ételt. Sokszor visszakérdez "
            "az alapfogalmakra és türelmesen várja a részletes útmutatást."
        ),
        patience=0.9,
        expertise=0.1,
        verbosity=0.7,
        frustration_tolerance=0.8,
        clarity_of_communication=0.6,
        technical_level=0.2,
    ),
    "budget_student": UserPersona(
        id="budget-student",
        name="Budget Student",
        description=(
            "Egyetemista kevés pénzből, alap konyhai felszereléssel. Olcsó, "
            "egyszerű recepteket kér, gyakran kér olcsóbb alapanyag-alternatívát."
        ),
        patience=0.8,
        expertise=0.3,
        verbosity=0.6,
        frustration_tolerance=0.6,
        clarity_of_communication=0.5,
        technical_level=0.3,
    ),
    "health_conscious_foodie": UserPersona(
        id="health-conscious-foodie",
        name="Health Conscious Foodie",
        description=(
            "Egészségtudatos foodie, érdekli makrók, zsírtartalom, "
            "teljes kiőrlésű / kevesebb cukor opciók."
        ),
        patience=0.7,
        expertise=0.6,
        verbosity=0.7,
        frustration_tolerance=0.6,
        clarity_of_communication=0.8,
        technical_level=0.6,
    ),
}


def create_custom_persona(**overrides) -> UserPersona:
    """Egyedi persona a beginner_cook alap persona felülírásával."""
    base = PREDEFINED_PERSONAS["beginner_cook"].model_dump()
    base.update(overrides)

    if "id" not in overrides:
        import time

        base["id"] = f"custom-{int(time.time() * 1000)}"

    return UserPersona(**base)
