from typing import Dict
from .types import ConversationGoal



PREDEFINED_GOALS: Dict[str, ConversationGoal] = {
    'vague_memory_recall': ConversationGoal(
        id='vague-memory-recall',
        description='Homályos, pontatlan kérdések feltevése korábban tárolt információkról, hogy tesztelje az asszisztens pontosító kérdéskezelését.',
        success_criteria=[
            'Az asszisztens felismeri, hogy a kérdés túl homályos, és pontosítást kér.',
            'A felhasználó válaszol a pontosító kérdésekre.',
            'Az asszisztens a kapott pontosítás alapján megpróbálja visszakeresni a megfelelő információt.',
            'A felhasználó vagy megkapja a választ, vagy megérti, miért nem található a keresett információ.',
        ],
        expected_turns=4,
        domain='general',
        complexity='moderate',
    ),

    'specific_memory_recall': ConversationGoal(
        id='specific-memory-recall',
        description='Nagyon konkrét kérdések feltevése a tárolt információkról, hogy tesztelje a közvetlen visszakeresést.',
        success_criteria=[
            'Az asszisztens azonnal megpróbálja visszakeresni a konkrét információt.',
            'Az asszisztens megadja a választ, ha megtalálta, vagy elmagyarázza, ha nem.',
            'Nem tesz fel felesleges pontosító kérdéseket egyértelmű kérés esetén.',
        ],
        expected_turns=2,
        domain='general',
        complexity='simple',
    ),

    'multi_clarification_memory': ConversationGoal(
        id='multi-clarification-memory',
        description='Rendkívül homályos kérdések feltevése, amelyek több körös pontosítást igényelnek.',
        success_criteria=[
            'Az asszisztens megfelelő, releváns pontosító kérdéseket tesz fel.',
            'Az asszisztens több körön át is képes megtartani a kontextust.',
            'A felhasználó végül elég konkrét információt ad a kereséshez.',
            'Az asszisztens sikeresen visszakeresi az információt, vagy elmagyarázza, miért nem található.',
        ],
        expected_turns=6,
        domain='general',
        complexity='complex',
    ),

    'resist_clarification': ConversationGoal(
        id='resist-clarification',
        description='Annak tesztelése, hogyan kezeli az asszisztens azokat a felhasználókat, akik nem szívesen adnak pontosítást.',
        success_criteria=[
            'Az asszisztens kitartóan, de udvariasan próbál pontosítást kérni.',
            'Az asszisztens elmagyarázza, miért szükséges a pontosítás.',
            'Az asszisztens megfelelően kezeli a felhasználó frusztrációját.',
            'Az asszisztens vagy megszerzi a szükséges információt, vagy világosan elmagyarázza, miért nem tud segíteni.',
        ],
        expected_turns=5,
        domain='general',
        complexity='moderate',
    ),

    'memory_storage_test': ConversationGoal(
        id='memory-storage-test',
        description='A felhasználó információt oszt meg tárolásra, majd később homályos kérdésekkel teszteli a visszakeresést.',
        success_criteria=[
            'Az asszisztens sikeresen eltárolja a megosztott információt.',
            'Később, homályos kérdés esetén pontosítást kér.',
            'A pontosítás után az asszisztens vissza tudja keresni a tárolt információt.',
        ],
        expected_turns=6,
        domain='general',
        complexity='moderate',
    ),
}


def create_custom_goal(**overrides) -> ConversationGoal:
    """Egyedi beszélgetési cél létrehozása megadott felülírásokkal."""
    base = PREDEFINED_GOALS['learn_basic_concept'].model_dump()
    base.update(overrides)

    if 'id' not in overrides:
        import time
        base['id'] = f'custom-goal-{int(time.time() * 1000)}'

    return ConversationGoal(**base)
