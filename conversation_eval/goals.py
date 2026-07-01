from typing import Dict

from .types import ConversationGoal

PREDEFINED_GOALS: Dict[str, ConversationGoal] = {
    "recipe_discovery": ConversationGoal(
        id="recipe-discovery",
        description=(
            'Homályos emlék alapján (pl. "valami thai tészta mogyoróval") az '
            "asszisztens segítsen beazonosítani a pontos receptet és adja meg "
            "az elkészítést."
        ),
        success_criteria=[
            "Az asszisztens legalább 1-2 releváns receptet felajánl a leírás alapján.",
            "A felhasználó választása után a teljes recept (hozzávalók + lépések) megjelenik.",
        ],
        expected_turns=3,
        domain="gastronomy",
        complexity="moderate",
    ),
    "ingredient_swap": ConversationGoal(
        id="ingredient-swap",
        description=(
            "Egy konkrét recept kiválasztása, majd rákérdezés egy hiányzó vagy "
            "drága alapanyag helyettesítésére (pl. budget alternatíva)."
        ),
        success_criteria=[
            "Az asszisztens azonosítja a receptet a gyűjteményben.",
            "Szakmailag releváns és logikus helyettesítőt javasol.",
        ],
        expected_turns=3,
        domain="gastronomy",
        complexity="moderate",
    ),
    "step_by_step_guide": ConversationGoal(
        id="step-by-step-guide",
        description=(
            "Egy konkrét recept interaktív elkészítése, lépésenként haladva, "
            "technikai magyarázatokat kérve."
        ),
        success_criteria=[
            "Az asszisztens azonosítja a pontos receptet.",
            "Nem ömleszti rá a teljes szöveget a felhasználóra, követi a kért tempót.",
            'Képes megmagyarázni a technikai részleteket (pl. mi az a "közepes láng").',
        ],
        expected_turns=6,
        domain="gastronomy",
        complexity="complex",
    ),
    "dietary_filtering": ConversationGoal(
        id="dietary-filtering",
        description=(
            "Vacsora javaslat kérése szigorú megkötéssel: mogyoró-, gluténmentes "
            "vagy alacsony szénhidráttartalmú opció kell."
        ),
        success_criteria=[
            "Az asszisztens nem javasol olyan ételt, ami tartalmazza az allergént.",
            "Több opció esetén indokolja a választást.",
        ],
        expected_turns=3,
        domain="gastronomy",
        complexity="moderate",
    ),
    "recipe_variant_suggestion": ConversationGoal(
        id="recipe-variant-suggestion",
        description=(
            "Létező recepthez variációkat kér a user (pl. hogyan legyen vegán vagy "
            "kevésbé zsíros), az asszisztens konkrét módosításokat javasol."
        ),
        success_criteria=[
            "Az asszisztens azonosítja az alapreceptet.",
            "Követhető és szakmailag helyes módosításokat javasol.",
            "A javaslatok illeszkednek az étel jellegéhez.",
        ],
        expected_turns=3,
        domain="gastronomy",
        complexity="moderate",
    ),
    "menu_planning": ConversationGoal(
        id="menu-planning",
        description=(
            "Több fogásos menü összeállítása a korpuszból "
            "(pl. thai vacsora előétellel és főétellel)."
        ),
        success_criteria=[
            "Az asszisztens több, egymáshoz passzoló receptet javasol a gyűjteményből.",
            "A javaslatok egy közös téma köré épülnek.",
        ],
        expected_turns=4,
        domain="gastronomy",
        complexity="complex",
    ),
}


def create_custom_goal(**overrides) -> ConversationGoal:
    """Egyedi goal a recipe_discovery alap felülírásával."""
    base = PREDEFINED_GOALS["recipe_discovery"].model_dump()
    base.update(overrides)

    if "id" not in overrides:
        import time

        base["id"] = f"custom-goal-{int(time.time() * 1000)}"

    return ConversationGoal(**base)
