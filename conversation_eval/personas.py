from typing import Dict
from .types import UserPersona


# ---------------------------------------------------------------------------
# ELŐRE DEFINIÁLT PERSONÁK
#
# Ezek a personák különböző felhasználói viselkedéseket modelleznek.
# A céljuk: a memória-asszisztens különböző helyzetekben való teljesítményének
# tesztelése (pl. homályos kérdések, frusztráció, pontosítási körök).
# ---------------------------------------------------------------------------

PREDEFINED_PERSONAS: Dict[str, UserPersona] = {

    # -----------------------------------------------------------------------
    # 1) Homályosan kommunikáló felhasználó
    #    → teszteli, hogy az asszisztens mennyire jól kérdez vissza
    # -----------------------------------------------------------------------
    'vague_communicator': UserPersona(
        id='vague-communicator',
        name='Vague Communicator',
        description='Olyan felhasználó, aki homályos, nehezen értelmezhető kérdéseket tesz fel a tárolt emlékeivel kapcsolatban, így tesztelve a pontosító kérdések kezelését.',
        patience=0.6,
        expertise=0.4,
        verbosity=0.3,
        frustration_tolerance=0.5,
        clarity_of_communication=0.2,  # Szándékosan alacsony → homályos kérdések
        technical_level=0.3,
    ),

    # -----------------------------------------------------------------------
    # 2) Segítőkész, jól pontosító felhasználó
    #    → ideális partner, aki szépen válaszol a visszakérdezésekre
    # -----------------------------------------------------------------------
    'clarification_cooperative': UserPersona(
        id='clarification-cooperative',
        name='Clarification Cooperative',
        description='Segítőkész felhasználó, aki világos és hasznos pontosításokat ad, amikor az asszisztens rákérdez.',
        patience=0.8,
        expertise=0.5,
        verbosity=0.6,
        frustration_tolerance=0.7,
        clarity_of_communication=0.8,
        technical_level=0.4,
    ),

    # -----------------------------------------------------------------------
    # 3) Pontosítást elutasító, frusztrált felhasználó
    #    → teszteli, hogyan kezeli az asszisztens a nehéz ügyfeleket
    # -----------------------------------------------------------------------
    'clarification_resistant': UserPersona(
        id='clarification-resistant',
        name='Clarification Resistant',
        description='Olyan felhasználó, aki frusztrálttá válik a pontosító kérdésektől, és nem szívesen ad meg részleteket.',
        patience=0.2,
        expertise=0.3,
        verbosity=0.4,
        frustration_tolerance=0.3,
        clarity_of_communication=0.4,
        technical_level=0.2,
    ),

    # -----------------------------------------------------------------------
    # 4) Sok memóriát használó felhasználó
    #    → gyakran kérdez vissza, különböző részletességgel
    # -----------------------------------------------------------------------
    'memory_heavy_user': UserPersona(
        id='memory-heavy-user',
        name='Memory Heavy User',
        description='Olyan felhasználó, aki rengeteg információt tárol, és gyakran próbálja ezeket visszakeresni — hol nagyon pontosan, hol csak nagy vonalakban.',
        patience=0.7,
        expertise=0.6,
        verbosity=0.7,
        frustration_tolerance=0.6,
        clarity_of_communication=0.6,
        technical_level=0.5,
    ),

    # -----------------------------------------------------------------------
    # 5) Nagyon pontos kérdező
    #    → teszteli, hogy az asszisztens képes-e direkt módon előhívni memóriát
    # -----------------------------------------------------------------------
    'precise_questioner': UserPersona(
        id='precise-questioner',
        name='Precise Questioner',
        description='Olyan felhasználó, aki nagyon konkrét kérdéseket tesz fel a tárolt emlékeiről, ezzel a közvetlen visszakeresést tesztelve.',
        patience=0.5,
        expertise=0.7,
        verbosity=0.5,
        frustration_tolerance=0.5,
        clarity_of_communication=0.9,  # Nagyon tiszta kommunikáció
        technical_level=0.6,
    ),

    # -----------------------------------------------------------------------
    # 6) Extrém módon homályos felhasználó
    #    → több környi pontosítást igényel, nehéz eset
    # -----------------------------------------------------------------------
    'extremely_vague': UserPersona(
        id='extremely-vague',
        name='Extremely Vague',
        description='Olyan felhasználó, aki rendkívül kétértelmű, homályos kérdéseket tesz fel, ezért több környi pontosítást igényel.',
        patience=0.4,
        expertise=0.2,
        verbosity=0.3,
        frustration_tolerance=0.4,
        clarity_of_communication=0.1,  # Szinte teljesen érthetetlen
        technical_level=0.1,
    ),
}


# ---------------------------------------------------------------------------
# EGYEDI PERSONA LÉTREHOZÁSA
# ---------------------------------------------------------------------------
def create_custom_persona(**overrides) -> UserPersona:
    """
    Egyedi persona létrehozása tetszőleges felülírásokkal.
    A PREDEFINED_PERSONAS['average_user'] lesz az alap,
    és az overrides paraméterben megadott mezők felülírják azt.

    Ha nincs külön ID megadva, automatikusan generálunk egyet.
    """
    base = PREDEFINED_PERSONAS['average_user'].model_dump()
    base.update(overrides)

    if 'id' not in overrides:
        import time
        base['id'] = f'custom-{int(time.time() * 1000)}'

    return UserPersona(**base)
