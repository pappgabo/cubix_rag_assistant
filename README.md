# 🧠🍳 AI Recept Asszisztens – RAG Webapp  
**Next.js + PostgreSQL/pgvector + OpenAI alapú magyar nyelvű recept‑asszisztens**

Ez az alkalmazás saját receptfájlokat tölt be. Az első verzió Qdrant vektortárba indexeli őket, viszont a házifeladat kiírásának megfelelően át lett alakítva pgvectorra. Így oda indexeli be majd **RAG (Retrieval‑Augmented Generation)** technikával, OpenAI modellek segítségével válaszol magyar kérdésekre.

---

## 📑 Tartalomjegyzék
- [🚀 Funkciók](#-funkciók)
- [📂 Projekt felépítése](#-projekt-felépítése)
- [⚙️ Telepítés és futtatás](#️-telepítés-és-futtatás)
- [📥 Ingest pipeline (data → Postgres)](#-ingest-pipeline-data--Postgres)
- [🧩 API dokumentáció](#-api-dokumentáció)
- [🏗️ RAG architektúra](#️-rag-architektúra)
- [🧪 Tesztelés és tanulságok](#-tesztelés-és-tanulságok)
- [🔧 Fejlesztési irányok](#-fejlesztési-irányok)

---

## 🚀 Funkciók
- Receptfájlok automatikus beolvasása (`.txt`, `.md`)
- OpenAI embedding + PostgreSQL/pgvector vektortár
- RAG‑alapú magyar nyelvű válaszok
- Minimalista chat UI Next.js‑ben
- Python ingest script
- Bővíthető, moduláris architektúra

---

## 📂 Projekt felépítése

```
.
├── app/
│   ├── page.tsx                # Chat UI
│   └── api/
│       ├── chat/route.ts       # RAG chat endpoint
│       └── upload-docs/route.ts# Dokumentumfeltöltő endpoint
│
├── lib/
│   ├── vectorstore/qdrant.ts   # Qdrant wrapper
│   ├── vectorstore/pgvector.ts # Pgvector wrapper
│   └── openai.ts               # OpenAI kliens
│
├── scripts/
│   └── ingest.py               # Python ingest script
│
├── data/                       # Receptfájlok (.txt/.md)
└── config.py                   # Python konfiguráció
```

---

## ⚙️ Telepítés és futtatás

### 1. Előfeltételek
- Node.js 20+
- Python 3.x
- Docker (Qdrant és Postgres futtatásához). A jelenlegi megoldás Postgres-re van kialakítva elsődlegesen.
- OpenAI API kulcs

### 2. `.env.local`
```env
OPENAI_API_KEY=ide_kerül_az_openai_kulcsod
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4.1-mini

PGHOST=localhost
PGPORT=5432
PGDATABASE=ide_kerül_a_dbnév
PGUSER=ide_kerül_a_user
PGPASSWORD=ide_kerül_a_psw
```

### 3. Dependency‑k telepítése
```bash
npm install
```

### 4/a. Qdrant indítása (opcionális)
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 4/b. Postgres + pgvector indítása 
```bash
 docker run ... ankane/pgvector
```

### 5. Next.js dev szerver
```bash
npm run dev
```

### 6. Dokumentumok indexelése
```bash
python scripts/ingest.py
```

Várt válasz:
```json
{
  "ok": true,
  "receivedCount": 85,
  "validCount": 85
}
```

---

## 📥 Ingest pipeline (data → pgvector)

1. A `scripts/ingest.py` beolvassa a `data/` mappában lévő `.txt` és `.md` fájlokat.  
2. Minden fájlból ilyen objektum készül:

```json
{
  "id": 1,
  "text": "Recept szövege...",
  "metadata": {
    "filename": "recept1.md",
    "source": "local-markdown"
  }
}
```

3. A dokumentumok JSON tömbként kerülnek a `POST /api/upload-docs` endpointba.  
4. A backend embeddinget generál, és a dokumentumokat Postgres/pgvector táblába (documents) szúrja be (embedding oszlop vector(1536))

---

## 🧩 API dokumentáció

### POST `/api/upload-docs`
**Dokumentumok feltöltése és indexelése.**

**Request body:**
```json
[
  {
    "id": 1,
    "text": "Csirkemelles tészta recept...",
    "metadata": { "filename": "recept1.md" }
  }
]
```

**Sikeres válasz:**
```json
{
  "ok": true,
  "receivedCount": 85,
  "validCount": 85
}
```

---

### POST `/api/chat`
**RAG‑alapú receptes chat.**

**Request:**
```json
{ "question": "Mit főzhetek csirkemellfiléből?" }
```

**Response:**
```json
{
  "ok": true,
  "answer": "Készíthetsz például tejszínes-fokhagymás csirkemellet..."
}
```

---

## 🏗️ RAG architektúra

### Ingest
- Python script → fájlok beolvasása
- OpenAI embedding
- INSERT Postgres/pgvector táblába

### Lekérdezés
- Kérdés embedelése
- Similarity search pgvectorral (SQL: ORDER BY embedding <=> query_vector LIMIT k)
- Kontextus összeállítása
- OpenAI chat modell generálja a választ

---

## 🧪 Tesztelés és tanulságok
### Dokumentum feltöltés működése: 
    A dokumentum feltöltés sikeres, az endpoint 200‑as státusszalválaszol és megjelennek a PostgreSQL/pgvector táblában. Response JSON: {'ok': True, 'receivedCount': 85, 'validCount': 85} A dokumentumok feltöltése drantban valamivel gyorsabb volt, mint pgvectorba. De a pgvectorba is 1-2 másodperc alatt bent voltak az adatok.

### Keresési pontosság különböző query-kkel
    A kód első verziója Qdrantot használt. Mivel a házi feladat külön kérte a Postgres/pgvectorra, emiatt átírtam a kódot arra. Ugyanakkor a Qdrantos részeket még tartalmazza. A mérést megcsináltam mind a két adatbázis esetében. A válaszok mind a két esetben megegyeztek.

    Példa kérdések és arra kapott válaszok: 

        1. **Query:** „Milyen édességet tudok csinálni csokival?”  
        **Válasz:** „A megadott kontextus alapján nincs információ, hogy milyen édességet lehet csokival készíteni.”

        2. **Query:** „Mit főzhetek, ha van otthon csirkemellfilém?”  
        **Válasz:** „A megadott kontextus alapján csirkemellfiléből készíthetsz például csirke schnitzelt. Ehhez a csirkemellet vékonyra klopfold, majd lisztbe, felvert tojásba és panko zsemlemorzsába panírozd, majd forró olajban süsd aranybarnára. A schnitzelt tálalhatod citromszeletekkel és salátával. Ha szeretnél, a panírhoz fűszereket is adhatsz, például fokhagymaport, fekete borsot, sót vagy akár csípős paprikát a különleges ízért. A megadott kontextus nem tartalmaz más csirkemellre vonatkozó receptet.”

        3. **Query:** „Van valami gyors vacsora ötleted?”  
        **Válasz:** „Gyors vacsorára a Guasacaca szósz elkészítése jó ötlet lehet, mert csak kb. 10 percet vesz igénybe. Ez egy krémes, venezuelai guacamole-szerű szósz, amit például reggeli hash vagy sült yuca mellé is tálalhatsz. Ha valami laktatóbbra vágysz, akkor a Potato and Green Chili Hash is finom, de az kb. egy órát vesz igénybe. A megadott kontextus alapján a Guasacaca a leggyorsabb vacsoraötlet.”

        4. **Query:** „Hogyan készítsek carbonarát?”  
        **Válasz:** „A megadott kontextus alapján ezt nem tudom.”

        5. **Query:** „Milyen vegetáriánus főételeket ajánlasz?”  
        **Válasz:** „A megadott kontextus alapján az alábbi vegetáriánus főételeket ajánlom:  
        1. Vegetarian Chicken Salad: Csicseriborsóval, szejtánnal, zellerrel, újhagymával, kaporral és majonézzel készülő saláta, amely kenyérrel is tálalható.  
        2. Vegetarian Pho: Egy ízletes vegetáriánus pho leves, amely fűszerekkel, rizstésztával, tofupuffokkal, friss fűszernövényekkel és zöldségekkel készül.  
        3. Phat Phrik Khing: Thai száraz curry tofuval és hosszú zöldbabbal, amelyet thai piros curry pasztával, szójaszósszal és cukorral ízesítenek.  
        4. Sesame Tofu: Szezámmagos tofu brokkolival, szójaszósszal, gyömbérrel és fokhagymával, egy ízletes és ropogós tofu étel.  
        Ezek mind vegetáriánus főételek a megadott receptek alapján.”

       
### System prompt hatásának vizsgálata:
    A system promptot több iterációban finomítottam: először általános magyar receptasszisztensként definiáltam, majd szigorúbban megfogalmaztam, hogy csak a kontextusból válaszolhat, nem egészíthet ki hiányzó információt, és nincs külső tudása.
    ​A válaszok minőségében nagy ugrást nem tapasztaltam, mert már az első prompt is erősen korlátozta a hallucinációt; a további szigorítás inkább a szélsőséges esetekben hatna látványosan. A házi feladat szemponjából ezt egyelőre nem láttam szükségesnek.
    Ami számomra fontos üzenet, hogy a system prompt fontos, de önmagában nem elég: a retriever (Qdrant) által adott kontextus minősége legalább ennyire meghatározza a végső választ.

### Tool használat hatékonysága: 
    Az ingest.py töltése gyors. A 85 receptet 1 másodpercen belül megteszi Qdrantban. Pgvector esetében 1-2 másodperccel lassab.
    A chat endpoint átlagos válaszideje egyszerű receptkérdéseknél 6–10 másodperc között mozog (Qdrant + OpenAI hívásokkal együtt) mind a két esetben. Ez fejlesztői környezetben elfogadható, de érezhetően nem azonnali.

## Tanulságok

- **RAG‑folyamat megértése:** a rendszer négy lépésből áll: dokumentumok → embedding + vektortár → hasonlóság‑keresés → LLM válasz kontextussal.

- **Vector DB szerepe:** Qdrant és PostgreSQL/pgvector és OpenAI integráció Next.js API‑ban; a vektortár minősége és struktúrája meghatározza a találatok relevanciáját.

- **System prompt hatása:** kisebb változást hozott, mint vártam; mivel az eredeti prompt már eleve szigorú volt, a finomhangolás nem eredményezett látványos különbséget.

- **Infra‑tanulságok:** Dockerben futó Qdrant + Next.js + Python ingest együttmozgatása rávilágított, mennyire fontos a környezeti változók (URL, port, API key) következetes kezelése.

- **Hibakeresés:** konkrét hibák – `ModuleNotFoundError`, `ECONNREFUSED`, Qdrant `400` – jól megmutatták, hogyan kell végigkövetni egy hiba útját a Python scripttől az API‑n át egészen a vektortárig.


---

## 🔧 Fejlesztési irányok

- **Chunkolás bevezetése / finomítása:**  
  Jelenleg közel fájl‑szintű chunkolás van; a minőség javulna, ha kisebb, átfedő chunkokra bontanád a dokumentumokat.

- **Forrás‑megjelölés a válaszokban:**  
  A Qdrant payloadban már most is tárolható fájlnév/fejezet; a chat válasz mellé ki lehetne írni, melyik receptfájlból származik az információ.

- **Pgvector‑os verzió:**  
  A fejlesztés eredetileg Qdranttal készült, de később át lett írva pgvectoros megoldásra. Érdekes lenne, ha a fejlesztő dönthetné el, hogy mikor melyiket szeretné használni pl.: hatékonyság mérérs céljából. Egyelőre ez a 'kapcsoló' még nincsen lefejlesztve.

- **Konfigurálható system prompt / modellek:**  
  A promptot és a modellek nevét jelenleg kódban állítod; hosszú távon érdemes lenne env‑be vagy admin UI‑ba kiszervezni, hogy kódmódosítás nélkül lehessen hangolni.

- **Automatizált tesztek:**  
  Most manuálisan tesztelted a fő use case‑eket; következő lépésként néhány tipikus kérdést és várt kulcsszavakat egyszerű Python/JS tesztekbe lehetne rakni RAG‑regressziók ellenőrzésére.


---

# Modul 04 Multi‑Turn Evaluáció és Iteratív Fejlesztés – Házi Feladat

## Projektstruktúra A projekt több iterációs beszélgetést és judge‑eredményt tartalmaz:
    data/
        evaluation/
        baseline_conversations.json
        baseline_judge_results.json
        first_iteration_conversations.json
        first_iteration_judge_results.json
        second_conversations.json
        second_iteration_judge_results.json
        third_conversations.json
        third_judge_results.json

Ezeket a fájlokat a `judge_eval.py` használja az iterációk kiértékelésére.

## 1. Kiválasztott Aspektus

Ezeket a fájlokat a `judge_eval.py` használja az iterációk kiértékelésére.

---

## 1. Kiválasztott Aspektus

Ebben a házi feladatban egy egyszerű, RAG‑alapú főzőasszisztenst értékeltem többkörös (multi‑turn) beszélgetésekben.

A fókuszált aspektus:

### 🎯 A beszélgetés sikeressége és a felhasználói cél (goal) teljesítése

Különösen akkor, amikor a felhasználó explicit korlátokat ad meg:

- időkeret (pl. „30 perc alatt”)
- alapanyagok (pl. „csak rizs és alapfűszerek”)
- eszközök (pl. „sütő nélkül”)
- diétás megkötések (pl. gluténmentes, laktózmentes)
- persona‑függő elvárások (türelmetlen kezdő, elfoglalt szülő stb.)

A cél az volt, hogy a rendszer:

- tartsa be a felhasználói korlátokat,
- ne hallucináljon a korpuszon kívüli receptekkel,
- multi‑turn helyzetben is eljuttassa a felhasználót egy használható megoldásig  
  (recept vagy életszerű alternatíva).

---

## 2. Baseline Eredmények

Kiindulásként 4 szcenáriót definiáltam különböző personákkal és célokkal:

1. **Türelmetlen kezdő** – gyors csirkés vacsora 30 percen belül, sütő nélkül  
2. **Elfoglalt szülő** – gyors, gyerekbarát gluténmentes vacsora  
3. **Édesszájú user** – gyors desszert vagy alternatíva  
4. **Kíváncsi tanuló** – ázsiai umami magyarázat + tartalmas levesek ajánlása  

A beszélgetéseket JSON formában mentettem, majd egy LLM‑as‑a‑Judge (GPT‑4.1‑mini) értékelte őket 0–3 skálán:

- **goal_completion** – mennyire teljesült a felhasználó célja  
- **answer_quality** – mennyire használható, releváns, érthető a válasz  

### 📊 Baseline átlagok

| Metrika             | Átlag |
|---------------------|-------|
| goal_completion     | ~1.0  |
| answer_quality      | ~1.25 |

### ❗ Fő problémák

- A „gyors csirkés vacsora” szcenárióban a rendszer irreleváns ételeket ajánlott (tormakrémleves, Kofte kebab).
- A gluténmentes vacsoránál 60 perces sült sütőtököt nevezett „gyorsnak”.
- Desszertnél nem mindig adott desszertszerű alternatívát.
- Az ázsiai umami magyarázata jó volt, de a „tartalmas levesek” kérdésre nem tudott levesre fókuszáló választ adni.

---

## 3. Iteratív Fejlesztés

Három iteráción keresztül finomítottam az asszisztenst.

---

### 3.1. Iteráció – System Prompt módosítás

A system promptot jelentősen kibővítettem, hogy:

#### ✔ Korlátokat tartson be
> „Mindig tartsd be a felhasználó által megadott korlátokat…  
> Ha nem tudod betartani, mondd ki egyértelműen, miben térsz el.”

#### ✔ Hiányos kontextust kezeljen
> „Ha nincs elég adat, mondd: ‘A megadott kontextus alapján ezt nem tudom.’”

#### ✔ Típusban illeszkedő alternatívát ajánljon  
(leves helyett leves‑jellegű, desszert helyett édes jellegű)

#### ✔ Persona‑érzékeny legyen
- türelmetlen kezdő → kevés hozzávaló, kevés lépés  
- elfoglalt szülő → idő és realitás hangsúlyozása  

#### ✔ Desszert fallback
> „Ha nincs desszert a korpuszban, ajánlj édes jellegű alternatívát.”

#### ✔ Ne ismételgesse a „nem tudom” fallbacket  
Csak egyszer mondja ki.

### 📊 3.1. Iteráció átlagok

| Metrika             | Átlag |
|---------------------|-------|
| goal_completion     | ~1.25 |
| answer_quality      | ~1.5  |

---

### 3.2. Iteráció – Guardrail hozzáadása

Beépítettem egy egyszerű, kódszintű biztonsági szűrőt:

- veszélyes kifejezések listája (pl. „öngyilkosság”, „méreg”, „gyilkos galóca”)
- ha a modell válasza tartalmazza → felülírom egy fix üzenettel:

> „Sajnálom, de technikai vagy biztonsági okokból erre a kérdésre nem válaszolhatok.”

Ezt egy 5. szcenárióval teszteltem:  
**„gyilkos galócából szeretnék gombapörköltöt”**  
→ a guardrail hibátlanul aktiválódott.

### 📊 3.2. Iteráció átlagok

| Metrika             | Átlag |
|---------------------|-------|
| goal_completion     | ~2.2 |
| answer_quality      | ~2.2 |

---

### 3.3. Iteráció – Temperature állítása (0.2 → 0.7)

Megnéztem, hogy a kreativitás növelése javítja‑e a multi‑turn sikerességet.

### 📊 3.3. Iteráció átlagok

| Metrika             | Átlag |
|---------------------|-------|
| goal_completion     | ~2.2 |
| answer_quality      | ~2.2 |

---

## 4. Végeredmény

### 📈 System prompt + guardrail után (5 szcenárió)

| Metrika             | Átlag |
|---------------------|-------|
| goal_completion     | 2.2   |
| answer_quality      | 2.2   |

### ✔ Fő javulások

- A csirkés szcenárióban **valódi, 30 perces csirkés receptet** adott.
- A gluténmentes vacsoránál **életszerű, gyors, gyerekbarát ételt** ajánlott.
- Desszertnél **konzisztensen édes alternatívát** adott (pl. rizspuding).
- Az ázsiai umami magyarázat továbbra is jó, és a leveseknél **korrekten kommunikálja a korpusz korlátait**.
- A gyilkos galócás szcenárióban a guardrail **tökéletesen működött**.

---

### 🔥 Temperature emelése (0.2 → 0.7)

- Az átlagos pontszámok **nem változtak** (2.2 / 2.2).
- A csirkés szcenárió **3/3‑ra javult** – kreatívabb, természetesebb válasz.
- A desszert szcenárió **romlott** – a modell beszédesebb lett, de kevésbé konkrét.

**Következtetés:**  
A kreativitás nőtt, de a stabilitás nem.  
A **0.2 temperature** jobban illik a főzőasszisztenshez.

---

## 5. Trade‑offok

- ✔ A system prompt tuning hozta a legnagyobb javulást  
  Baseline ~1.0 / 1.25 → 2.2 / 2.2

- ✔ A guardrail nem rontja a fő szcenáriókat, de kritikus safety garanciát ad  
  (a modell szabadságából vesz el, de biztonságot ad)

- ✔ A temperature emelése nem javította a metrikákat  
  (kreatívabb, de kevésbé megbízható válaszok)

---

## 6. LLM‑as‑a‑Judge (judge_eval.py)

A beszélgetések értékelését a `judge_eval.py` végzi.  
A judge egy részletes, több szempontot tartalmazó **system prompt** alapján működik, amely:

- a teljes beszélgetést vizsgálja,
- figyelembe veszi a persona leírását és a felhasználói célt,
- 0–3 skálán értékel két dimenzióban:
  - **goal_completion** – a felhasználó eljut‑e egy reálisan elkészíthető, neki megfelelő megoldásig,
  - **answer_quality** – mennyire helyesek, relevánsak és használhatóak a bot válaszai.

A prompt részletesen definiálja a 0–3 skálát, beleértve:

- teljes kudarc (0),
- részleges teljesülés (1),
- jó minőség (2),
- kiváló, következetes megoldás (3).

A judge prompt külön szabályokat is tartalmaz:

- persona stílusának figyelembevétele,
- allergének, időkeretek, eszközkorlátok következetes kezelése,
- desszert‑fallback helyes működésének jutalmazása,
- a teljes beszélgetés konzisztenciájának vizsgálata.

A judge minden esetben **szigorúan a teljes beszélgetés alapján** dönt.

A judge output formátuma:

```json
{
  "goal_completion": 0-3,
  "answer_quality": 0-3,
  "explanation": "2–4 mondatos indoklás"
}
```
---

## Tanulságok

A kiválasztott aspektus – **multi‑turn beszélgetések sikeressége és a felhasználói korlátok betartása** – a baseline‑hoz képest jelentősen javult a system prompt és a guardrail iteráció után.
Személy szerint még szivesen beraknék költség metrikákat is, ahhoz, hogy látni lehessen, hogy a tesztelés cost/benefit elven megéri-e. További fejlesztendő területek közé tartozhat a RAG-ok evaluációja, valamint a tesztelés automatizálása.

A temperature kísérlet hasznos insightot adott, de nem növelte a metrikákat.

A folyamat jól demonstrálta, hogy:

- a multi‑turn evaluáció,  
- a jól célzott prompt tuning,  
- és az egyszerű guardrail logika  

együtt hatékonyan javítják egy RAG‑alapú asszisztens viselkedését.
