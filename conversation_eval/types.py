from typing import List, Optional, Dict, Any, Literal, Protocol
from datetime import datetime
from pydantic import BaseModel, Field


# A felhasználó szimulált személyiségét leíró modell.
# Ezek a paraméterek határozzák meg, hogyan viselkedik a "felhasználó"
# egy beszélgetési szimuláció során.
class UserPersona(BaseModel):
    id: str           # Egyedi azonosító
    name: str         # A persona neve
    description: str  # Rövid leírás a személyiségről

    # A következő mezők 0 és 1 közötti skálán mérik a jellemzőket:
    patience: float = Field(
        ge=0, le=1,
        description="0 = nagyon türelmetlen, 1 = nagyon türelmes"
    )
    expertise: float = Field(
        ge=0, le=1,
        description="0 = kezdő, 1 = szakértő"
    )
    verbosity: float = Field(
        ge=0, le=1,
        description="0 = tömör, 1 = bőbeszédű"
    )
    frustration_tolerance: float = Field(
        ge=0, le=1,
        description="0 = könnyen frusztrálódik, 1 = magas tűréshatár"
    )
    clarity_of_communication: float = Field(
        ge=0, le=1,
        description="0 = nagyon homályos kommunikáció, 1 = nagyon tiszta kommunikáció"
    )
    technical_level: float = Field(
        ge=0, le=1,
        description="0 = nem technikai, 1 = magas technikai szint"
    )


# A beszélgetés célját leíró modell.
# Ez határozza meg, hogy a szimuláció milyen eredményre törekszik.
class ConversationGoal(BaseModel):
    id: str  # Egyedi azonosító
    description: str  # A cél szöveges leírása
    success_criteria: List[str]  # Milyen feltételek teljesülése számít sikernek
    expected_turns: Optional[int] = None  # Várható párbeszéd-hossz (nem kötelező)

    # A beszélgetés témaköre
    domain: Literal['technical', 'general', 'business', 'creative', 'educational', 'gastronomy']

    # A cél komplexitása
    complexity: Literal['simple', 'moderate', 'complex']


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    turn_number: int
    latency_ms: int = 0


class SimulatedUserProtocol(Protocol):
    satisfied: bool

    def first_message(self) -> str: ...

    def next_message(self, state: ConversationState) -> Optional[str]: ...

    def is_satisfied(self) -> bool: ...


# A beszélgetés aktuális állapotát leíró modell.
class ConversationState(BaseModel):
    messages: List[Message]  # A teljes üzenetlista
    current_turn: int  # Aktuális kör száma
    goal_progress: float = Field(ge=0, le=1)  # A cél elérésének mértéke
    user_satisfaction: float = Field(ge=0, le=1)  # A felhasználó elégedettsége
    frustration_level: float = Field(ge=0, le=1)  # A frusztráció szintje
    context: Optional[Dict[str, Any]] = None  # Tetszőleges extra kontextusadatok


# A szimuláció konfigurációja.
# Ez határozza meg, milyen személyiséggel, céllal és paraméterekkel fut a szimuláció.
class SimulationConfig(BaseModel):
    persona: UserPersona  # A szimulált felhasználó
    goal: ConversationGoal  # A beszélgetés célja
    max_turns: int = 20  # Maximális üzenetszám
    api_endpoint: str  # Melyik API-t hívja a szimuláció
    simulation_id: str  # Egyedi azonosító
    seed: Optional[int] = None  # Random seed a reprodukálhatósághoz


# A szimuláció értékelésének metrikái.
# Ezeket a szimuláció végén számítjuk ki.
class EvaluationMetrics(BaseModel):
    goal_achieved: bool  # Sikerült-e elérni a célt
    total_turns: int  # Hány üzenetből állt a beszélgetés
    average_response_time: float  # Átlagos válaszidő (ms vagy más egység)
    user_satisfaction_score: float = Field(ge=0, le=1)  # Elégedettségi mutató
    clarity_score: float = Field(ge=0, le=1)  # Mennyire volt érthető a kommunikáció
    relevance_score: float = Field(ge=0, le=1)  # Mennyire volt releváns a válasz
    completeness_score: float = Field(ge=0, le=1)  # Mennyire volt teljes a válasz
    frustration_incidents: int  # Hányszor nőtt meg jelentősen a frusztráció
    error_rate: float = Field(ge=0, le=1)  # Hibaarány a válaszokban


# A teljes szimuláció eredménye.
# Ez tartalmazza a konfigurációt, a beszélgetést, a metrikákat és időadatokat.
class SimulationResult(BaseModel):
    config: SimulationConfig  # A szimuláció beállításai
    conversation: ConversationState  # A teljes beszélgetés állapota
    metrics: EvaluationMetrics  # A kiértékelés eredményei
    start_time: datetime  # Mikor indult a szimuláció
    end_time: datetime  # Mikor ért véget
    duration: float  # Időtartam ezredmásodpercben
    errors: Optional[List[str]] = None  # Esetleges hibák listája

