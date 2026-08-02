# Fázis 2 — tesztjegyzőkönyv

**Dátum:** 2026-08-02
**Branch:** `feature/phase-2-fastapi`
**Commit:** `e49c87e5`
**Tesztelő:** Papp Gábor

## Tesztkörnyezet

| Komponens | Érték |
|-----------|-------|
| FastAPI service | `uvicorn rag_service.main:app`, `http://127.0.0.1:8000` |
| Next.js | 16.1.1, `http://localhost:3000` |
| Konfiguráció forrása | `.env` (a Next.js indulási logja: `Environments: .env`) |
| Chat modell | `gpt-4.1-mini` |
| Embedding modell | `text-embedding-3-small` |
| Tesztkérdés | „Hogyan készül a hummus?" |

A `RAG_BACKEND` kizárólag a Next.js oldalt érinti, ezért `.env` módosítás után a
Next.js dev szerver újraindítása kötelező. Az uvicorn újraindítása nem szükséges,
csak a konzol tisztítása miatt történt minden kör elején.

---

## T-1 — Egységtesztek

**Cél:** a Fázis 2 kód konzisztenciájának offline ellenőrzése (`uv run pytest -q`),
elvárás 18 zöld teszt (14 × `test_core.py`, 4 × `test_rag_service.py`).

**Első futtatás:** megszakadt. A `uv.lock` fájlban bennmaradtak a merge konfliktus
jelölői (`<<<<<<< HEAD`, 1580. sor), amit az `uv` nem tud TOML-ként értelmezni. A
fájl újragenerálva: `Remove-Item uv.lock; uv lock; uv sync --group dev`.

**Eredmény: MEGFELELT.**

```text
..................                                                       [100%]
18 passed, 1 warning in 5.01s
```

A figyelmeztetés a `starlette.testclient`-től érkezik: a `httpx` használata
elavult, helyette `httpx2` ajánlott. Ez a `uv.lock` újragenerálása után felhúzott
frissebb csomagverzió következménye, a tesztek működését nem érinti.

---

## T-2 — Service mód, végponttól végpontig

**Cél:** annak bizonyítása, hogy a Next.js `/api/chat` a FastAPI-n keresztül éri el
a kanonikus `rag_core`-t, és nem futtat saját RAG-ot.

**Beállítás:** `RAG_BACKEND=service`, mindkét szerver újraindítva.

**Elvárás:** HTTP 200; az uvicorn konzolján megjelenik a `POST /v1/rag/query` sor;
a Next.js log `component` mezője `chat-proxy`.

**Eredmény: MEGFELELT.**

Uvicorn konzol:

```text
INFO:     127.0.0.1:51001 - "POST /v1/rag/query HTTP/1.1" 200 OK
INFO:     127.0.0.1:51007 - "POST /v1/rag/query HTTP/1.1" 200 OK
```

Python oldali fogyasztás (uvicorn konzol, első hívás):

```text
[LLM_USAGE] {"component": "rag-embed",    "totalTokens": 10,   "costUsd": 2e-07,     "latencyMs": 2938}
[LLM_USAGE] {"component": "rag-response", "totalTokens": 2438, "costUsd": 0.0004998, "latencyMs": 7562}
```

Next.js oldali log:

```text
[LLM_USAGE] {"component":"chat-proxy","totalTokens":0,"costUsd":0,"latencyMs":10846,"success":true}
 POST /api/chat 200 in 11.8s
```

A `chat-proxy` sor nulla tokent és nulla költséget mutat, mert a proxy nem látja a
Python oldalon keletkező fogyasztást. Ez a várt viselkedés, nem hiányzó adat.

**Válasz minősége:** a generált recept tartalmilag helyes és a korpuszra épül
(áztatás szódabikarbónával, 2 órás főzés, tahini elkészítése, za'atar a tetejére).
Visszaadott források: `hummus`, `baba-ganoush`, `lemon-tahini-dressing`,
`yemeni-hot-sauce`, `spicy-whole-grain-pub-mustard`.

---

## T-3 — Inline rollback

**Cél:** annak bizonyítása, hogy a TypeScript tartalék útvonal működik, és futó
FastAPI nélkül is kiszolgálja a kérést.

**Beállítás:** `RAG_BACKEND=inline`, mindkét szerver újraindítva.

**Elvárás:** HTTP 200; az uvicorn konzolján **nem** jelenik meg új sor; a Next.js
log `component` mezője `chat`, valós token- és költségértékekkel.

**Eredmény: MEGFELELT.**

Uvicorn konzol az indulás után (a hívás alatt sem bővült):

```text
INFO:     Application startup complete.
```

Next.js log:

```text
[LLM_USAGE] {"component":"rag-embed","totalTokens":10,  "costUsd":2e-7,      "latencyMs":625}
[LLM_USAGE] {"component":"chat",     "totalTokens":2447,"costUsd":0.00051645,"latencyMs":6015}
 POST /api/chat 200 in 6.9s
```

---

## T-2 és T-3 összevetése

| | uvicorn konzol | `component` | promptTokens | totalTokens | költség (USD) |
|--|--|--|--:|--:|--:|
| service | `POST /v1/rag/query 200 OK` | `chat-proxy` | 2140 | 2438 | 0,0004998 |
| inline | néma | `chat` | 2115 | 2447 | 0,00051645 |

A service sor token- és költségértékei a Python oldali `rag-response` sorból
származnak, mivel a `chat-proxy` bejegyzés ezeket nem tartalmazza.

---

## T-4 — A szolgáltatás nem elérhető

**Cél:** a hibaág ellenőrzése — `RAG_BACKEND=service` mellett leállított FastAPI.

**Beállítás:** `RAG_BACKEND=service`, Next.js újraindítva, majd az uvicorn
szándékosan leállítva.

**Elvárás:** HTTP 502 és az „A RAG service nem elérhető vagy hibát adott vissza"
üzenet; a hiba a monitoring logba is bekerül.

**Eredmény: MEGFELELT.**

HTTP válasz:

```text
HTTP 502
{"error":"A RAG service nem elérhető vagy hibát adott vissza."}
```

Monitoring log:

```text
component   success  errorMessage   latencyMs
chat-proxy  False    fetch failed   92
```

Két dolog érdemel figyelmet. Egyrészt a hiba nemcsak a felhasználóhoz jutott el,
hanem `success=false` értékkel a monitoringba is bekerült, tehát a hibaarány
mérhető. Másrészt a 92 ms-os latencia azt mutatja, hogy a rendszer azonnal
elhasal, nem vár ki hosszú időtúllépést — a felhasználó nem néz percekig üres
felületet.

A gyökérok a Next.js szerverkonzolján egyértelműen látszik:

```text
TypeError: fetch failed
    at async queryRagService (lib\chat\ragServiceClient.ts:36:16)
    at async POST (app\api\chat\route.ts:50:29)
  [cause]: AggregateError: { code: 'ECONNREFUSED' }
```

A strukturált logba viszont csak a nyers „fetch failed" szöveg kerül, a
`ECONNREFUSED` kód és a cél URL nem. Fejlesztés közben ez nem probléma, mert a
konzol ott van mellette; egy éles környezetben viszont, ahol csak a log marad,
nehezebb lenne megkülönböztetni a leállt szolgáltatást egy DNS- vagy
tanúsítványhibától.

**Felületi ellenőrzés:** hátravan.

---

## T-5 — Eval szintek újrafuttatása

**Cél:** annak igazolása, hogy a Fázis 2 nem okozott regressziót a RAG-, prompt- és
alkalmazásszintű kiértékelésben.

**Beállítás:** `RAG_BACKEND=service`, mindkét szerver fut. A beszélgetés-szimuláció
a Next.js `/api/chat` végpontján keresztül dolgozik, tehát a teljes láncot méri.

### T-5a — Alkalmazásszint (24 szimulált beszélgetés): MEGFELELT

| Mutató | Fázis 2 előtt | Most | Eltérés |
|--------|--------------:|-----:|--------:|
| `avg_goal_completion` | 2,58 | 2,375 | −0,205 |
| `avg_answer_quality` | 2,17 | 2,083 | −0,087 |

**Nincs regresszió.** A goal completion szórása 0,924, az átlag hibája 24 elemnél
0,189. Két független futás különbségének hibája ennek nagyjából a négyzetes
összege, körülbelül 0,27 — a mért 0,205-ös eltérés ennél is kisebb. Valódi
romláshoz nagyjából 0,55 pontos esés kellene. Az answer qualitynél az eltérés
(0,087) a hibahatár (0,199) felét sem éri el.

Technikai hiba nem torzította a mérést: a `conversations.json` egyetlen
`RENDSZERHIBA` bejegyzést sem tartalmaz.

Pontszám-eloszlás (0–3 skála):

```text
pontszám:  0   1   2   3
darab:     1   4   4  15
```

A beszélgetések 62%-a maximumot kapott. Ezen az eloszláson az átlag érzékeny
mutató: egyetlen beszélgetés egypontos elmozdulása 0,042-t mozdít rajta, tehát a
mért 0,2-es különbség nagyjából két beszélgetés ingadozásának felel meg.
Jelentésre alkalmasabb a „15 hibátlan, 5 elégtelen" bontás.

### T-5b — RAG szint: MEGFELELT

`rag_eval/rag_results.json`, `top_k=5`, 22 teszteset (ebből 20 ground truthszal).

| Stratégia | precision@5 | recall@5 | hit@5 | MRR@5 | F1@5 |
|-----------|------------:|---------:|------:|------:|-----:|
| `documents_baseline` | 0,180 | 0,659 | 0,750 | 0,692 | 0,258 |
| `documents_chunks` | 0,180 | 0,659 | 0,750 | 0,692 | 0,258 |
| `chunked_rerank` | 0,140 | 0,503 | 0,600 | 0,454 | 0,200 |

A precision@5 alacsonynak tűnő 0,18-as értéke félrevezető: a tesztesetek
többségében egyetlen elvárt dokumentum van, öt találat mellett tehát az
elméleti maximum 0,2. A mért érték ennek a 90%-a, vagyis gyakorlatilag a
plafonon van. Érdemi mutató itt a hit@5 és az MRR.

**A reranker mérhetően ront.** Minden mutatóban gyengébb a baseline-nál: a hit@5
0,75-ről 0,60-ra esik, az MRR pedig 0,692-ről 0,454-re — utóbbi 34%-os relatív
romlás. Ez a `docs/backlog.md` B-1 tételének számszerű bizonyítéka, és összecseng
a `rerank_score` mérésével (minden pontszám −9,5 alatt, azaz a modell egyik
találatot sem tartja relevánsnak).

A `documents_baseline` és a `documents_chunks` minden mutatóban azonos. Ez nem
feltétlenül hiba: a metrikák `base_id` szintre deduplikálnak, és a korpusz kicsi,
így a két tábla eltérő chunk-sorrendje ugyanarra a dokumentumlistára eshet össze.
A közvetlen API-tesztek ezzel egybevágnak (a nyers pontszámok kissé eltértek:
0,39226 kontra 0,39131). Egy alkalommal érdemes lenne ellenőrizni, hogy a
`chunked` ág valóban a chunk-táblát kérdezi-e.

### T-5b — Prompt szint: MEGFELELT

`prompt_eval/prompt_eval_results.json`, 18 teszteset.

| Mutató | Érték |
|--------|------:|
| `avg_context_relevance` | 4,44 / 5 |
| `avg_answer_quality` | 4,33 / 5 |
| `faithfulness` | 18× strong, 0× partial, 0× none |
| `avg_latency_ms` | 3 739 |

A hűség (faithfulness) mind a 18 esetben „strong": a rendszer egyetlen esetben sem
hallucinált a kontextuson túl. Ahol nem volt adat (q3 — indiai padlizsánkrém), ott
helyesen jelezte a hiányt.

#### A prompt szintű bíró vakfoltja

Ugyanez a futás tartalmaz egy önellentmondást, amit a bíró nem vett észre:

| Eset | Kérdés | Válasz | Bírói pontszám |
|------|--------|--------|----------------|
| q2 | Milyen alapanyagok kellenek a hummuszhoz? | „1/2 lb szárított csicseriborsó…" | 4 / strong |
| q18_spec | Melyik receptben használunk csicseriborsót? | „A megadott kontextus alapján egyik receptben sem." | **5 / strong** |

A korpuszban szerepel a `hummus` recept, ami csicseriborsót használ — ezt a q2
válasza ki is mondja, és a `rag_results.json` is tartalmazza a dokumentum
szövegét („1/2 lb dried chickpeas"). A q18_spec tehát **retrieval-hiba**: a
keresés nem hozta be a hummuszt, a modell pedig a kapott kontextushoz hűen,
helyesen mondta, hogy nincs ilyen recept.

A bíró ezt hibátlanra értékelte, mert a rendszerprompt szerint a **kontextushoz
való hűséget** méri, és nem látja sem a korpuszt, sem a visszakeresett chunkokat.
A prompt szintű kiértékelés ezért szerkezetileg vak a retrieval hibáira.

Ez nem a bíró hibája, hanem a mérési szintek elhatárolásának következménye, és
egyben a legjobb indoklás arra, miért kell **külön RAG szintű kiértékelés**
precision/recall/hit metrikákkal: az egyik szint azt méri, hogy a modell hű-e
ahhoz, amit kapott, a másik azt, hogy jót kapott-e egyáltalán. Egyik sem
helyettesíti a másikat.

#### Levágott válaszok

Két válasz (q5 — tarka dal, q7 — Pad See Ew) mondat közben megszakad. A bíró a
q7-nél észre is vette: „az utolsó lépés azonban félbeszakadt". Az ok a
`rag_core/generation.py` 67. sorában fixen beégetett `max_completion_tokens=400`.
Hosszú, lépéses recepteknél ez kevés. Lásd `docs/backlog.md`, B-8.

---

## A T-5a mélyebb elemzése — a hibák mintázata

A gyenge eredmények nem véletlenszerűen szórnak, hanem **feladattípus szerint**
csoportosulnak.

| Cél | n | átlag | | Persona | n | átlag |
|-----|--:|------:|--|---------|--:|------:|
| menu_planning | 4 | 3,00 | | impatient_chef | 6 | 2,67 |
| recipe_discovery | 4 | 2,75 | | budget_student | 6 | 2,50 |
| dietary_filtering | 4 | 2,50 | | health_conscious_foodie | 6 | 2,33 |
| recipe_variant_suggestion | 4 | 2,25 | | beginner_cook | 6 | 2,00 |
| step_by_step_guide | 4 | 2,00 | | | | |
| ingredient_swap | 4 | 1,75 | | | | |

A célok szerinti szóródás 1,25 pont, a personák szerinti 0,67. Nem az számít,
ki kérdez, hanem hogy mit.

A sorrend nem véletlenszerű: a három leggyengébb cél (`ingredient_swap`,
`step_by_step_guide`, `recipe_variant_suggestion`) mind **az előző fordulóra
hivatkozik** („mivel helyettesíthetem ebben", „mi a következő lépés", „adj egy
változatot erre"), míg a három legjobb (`menu_planning`, `recipe_discovery`,
`dietary_filtering`) egyetlen önálló kérdésből megválaszolható.

### A hiba mechanizmusa

A rendszer állapotmentes: a `route.ts` a kérésből egyedül a `question` mezőt
olvassa, a `RAGRequest` pedig nem tartalmaz beszélgetéstörténetet. Minden forduló
úgy indul, mintha az lenne az első. Ebből a következő lánc adódik:

1. A követő kérdés önmagában, töredékként jut a rendszerhez („és mivel
   helyettesíthetem?").
2. Az embedding és a pgvector keresés ezt a töredéket kapja, ezért irreleváns
   chunkokat ad vissza.
3. A system prompt a kontextushoz köti a modellt, ezért az helyesen elutasít.
4. A bíró ezt célteljesítési kudarcként pontozza.

A bíró indoklásai ezt szó szerint alátámasztják:

> „A bot az első válaszban adott egy jó példát a recept variálására, de a további
> kérésekre nem tudott érdemben reagálni, csak ismételte, hogy nem tud segíteni."

> „A második körben a felhasználó egyszerűbb megoldást kért, de a bot nem adott új
> választ."

Egy második, ettől független hiba is látszik: a mandulavaj helyettesítésére a
korpusz egyszerűen nem tartalmaz tudást, mert receptekből áll, nem helyettesítési
táblákból. Ez a korpusz hatókörének korlátja, nem implementációs hiba.

### Következtetés a Fázis 3-ra

A session management bevezetése mért indoklást kapott: a felhasználói szándékok
fele emlékezetet igényel, és pont ezek teljesítenek a leggyengébben.

Fontos tervezési tanulság, hogy **nem elég a beszélgetéstörténetet a promptba
tenni**. A hiba a fenti lánc 2. lépésénél kezdődik, a retrievalnél: ha a követő
kérdés töredékét embeddeljük, már rossz chunkokat kapunk, mielőtt a generálás
egyáltalán sorra kerülne. Szükség van a kérdés kontextualizálására is — a követő
kérdés átírására önálló kérdéssé a retrieval előtt.

**Módszertani fenntartás:** célonként csak 4 beszélgetés van, tehát az egyes
átlagok bizonytalansága nagy (nagyjából fél pont). Önmagában egyik célról sem
állítható, hogy szignifikánsan rosszabb. Ami erős, az a mintázat: mind a három
emlékezetigényes feladat az alsó felében van, mind a három önállóan
megválaszolható a felsőben.

---

## Összegzés

| Teszt | Állapot |
|-------|---------|
| T-1 Egységtesztek | **megfelelt** (18 zöld) |
| T-2 Service mód | **megfelelt** |
| T-3 Inline rollback | **megfelelt** |
| T-4 Szolgáltatás nem elérhető | **megfelelt** (felületi ellenőrzés hátravan) |
| T-5a Alkalmazásszintű eval | **megfelelt** (nincs regresszió) |
| T-5b RAG és prompt szintű eval | **megfelelt** |

A Fázis 2 központi állítása — hogy a prod és az eval ugyanazt a `rag_core` kódot
használja — a T-2 alapján igazolt. A rollback út a T-3 alapján valóban működik,
nem csak dokumentációban létezik. A T-4 azt mutatja, hogy a szolgáltatás kiesését
a rendszer gyorsan és megfigyelhetően kezeli. A T-5a igazolta, hogy az
alkalmazásszintű minőség nem romlott, egyben feltárta a rendszer legnagyobb
jelenlegi korlátját: az állapotmentességet. A T-5b mindkét szinten megfelelt, és
számszerű bizonyítékot adott arra, hogy a reranker ront a találatokon.

**A Fázis 2 tesztelése lezárva, a merge a `main`-be javasolt.** Egyetlen apró
nyitott pont maradt: a T-4 felületi ellenőrzése.

---

## A tesztelés során feltárt megfigyelések

Az alábbiak nem akadályozzák a működést, de érdemes rögzíteni őket. Amelyik tartós
tétel marad, azt később át kell emelni a `docs/backlog.md`-be.

**M-1 — A költségadat két forrásból áll össze service módban.** A `chat-proxy`
bejegyzés nullát mutat, a valós fogyasztás a Python oldali `rag-embed` és
`rag-response` sorokban van. Egy költségriportnak mindkét forrást össze kell adnia,
különben service módban nullát jelent.

**M-2 — A két útvonal prompthossza eltér.** Service módban 2140, inline-ban 2115
prompt token ugyanarra a kérdésre. A TypeScript rollback tehát nem bájtazonos mása
a Python útnak. Következmény: amíg inline módban fut a rendszer, az eval-eredmények
nem pontosan a futó viselkedést írják le.

**M-3 — Inline módban gyengébb a kérés-korreláció.** Az embedding sor `requestId`
mezője `embed-a320973e` alakú, ami nem egyezik a kérés azonosítójával; az
összekapcsolás csak `sessionId` alapján lehetséges. Service módban mindkét sor
azonos `requestId`-t visel.

**M-4 — A `RAG_BACKEND` csendben nyeli az elgépelést.** A kód csak a pontos
`inline` értéket ismeri fel, minden más service módot jelent. A teszt kezdetén a
`.env` `services` értéket tartalmazott, ami véletlenül helyesen működött, de
félrevezető. Egy ismeretlen érték melletti figyelmeztetés hasznos lenne.

**M-5 — A `rerank_score` nem jut el a Next.js válaszáig.** A `ragServiceClient.ts`
a chunkokból csak a `doc_id`, `base_id`, `text` és `score` mezőt képezi le. A
FastAPI-n keresztül a pontszám látható, a webes felületen nem.

**M-6 — Hibaágon pontatlan a session azonosító.** A `route.ts` `catch` ága mindig
`prod-<requestId>` értéket logol, akkor is, ha a kérésben érkezett `sessionId`. Egy
sikertelen eval-hívás így nem kereshető vissza a saját session-je alatt.

**M-7 — A `uv.lock` merge konfliktus jelölőkkel került commitba.** Generált fájl,
ezért kézi összefésülés helyett újragenerálandó. Javítva.
