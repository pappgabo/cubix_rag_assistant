# Ismert korlátok és backlog

> Tudatosan vállalt korlátok, mérési eredményekkel és a mögöttük álló döntéssel.
> Nem hibalista: minden tétel mellett szerepel, hogy miért nem blokkolja a
> jelenlegi működést, és mi lenne a következő lépés, ha sorra kerül.

---

## B-1 — A CrossEncoder reranker nem javít a találatokon

**Státusz:** nyitott, tudatosan halasztva
**Érintett kód:** `rag_core/reranker.py`, `RERANKER_MODEL` (`config.py`)
**Hatás a prodra:** nincs (lásd „Miért nem blokkoló")

### A megfigyelés

A `chunked_rerank` stratégia rosszabb sorrendet ad, mint a sima `chunked`.
Ez a fejlesztés korai szakaszában is látszott, de csak benyomás szintjén — a
`rerank_score` nem jött vissza az API-ból, így nem lehetett megmondani, hogy a
reranker rosszul rangsorol-e, vagy egyáltalán nem ad értékelhető jelet.

A `RetrievedChunk.rerank_score` mező bevezetése után a jelenség mérhetővé vált.

### Mérés

Kérdés: *„Hogyan készül a humusz?"*, `top_k=5`, `RAG_CANDIDATE_MULTIPLIER=4`.

| Stratégia | Találat | `score` (pgvector) | `rerank_score` (CrossEncoder) |
|-----------|---------|-------------------:|------------------------------:|
| `chunked` | hummus | 0,3913 | — |
| `chunked` | soft-pretzels-2 | 0,2827 | — |
| `chunked` | spicy-whole-grain-pub-mustard | 0,2651 | — |
| `chunked` | potato-and-green-chili-hash | 0,2649 | — |
| `chunked` | bagels | 0,2596 | — |
| `chunked_rerank` | hummus | 0,3913 | **-9,56** |
| `chunked_rerank` | baba-ganoush | 0,2200 | **-10,19** |
| `chunked_rerank` | carnitas-with-salsa-verde | 0,2336 | **-10,56** |
| `chunked_rerank` | vietnamese-pork-chops | 0,2156 | **-10,81** |
| `chunked_rerank` | halal-cart-chicken | 0,2087 | **-10,83** |

Két dolog olvasható ki. Egyrészt **minden pontszám -9,5 alatt van**: a
CrossEncoder nyers logitot ad vissza, ahol a nagyjából nulla feletti érték jelez
releváns találatot, a -10 körüli tartomány pedig azt, hogy a modell szerint a
passzusnak semmi köze a kérdéshez. A modell tehát mind az öt jelöltet
irrelevánsnak minősítette. Másrészt a **legjobb és a legrosszabb között alig 1,3
egység a különbség**, ami ilyen abszolút szint mellett zajnak tekintendő — a
sorrend gyakorlatilag véletlenszerű.

### Megerősítés RAG szintű metrikákkal

A `rag_eval` futása (22 teszteset, `top_k=5`, forrás:
`docs/phase-2-test-protocol.md` T-5b) számszerűsíti a romlást:

| Stratégia | precision@5 | recall@5 | hit@5 | MRR@5 |
|-----------|------------:|---------:|------:|------:|
| `documents_baseline` | 0,180 | 0,659 | 0,750 | 0,692 |
| `chunked_rerank` | 0,140 | 0,503 | 0,600 | 0,454 |

A reranker minden mutatóban gyengébb. A hit@5 0,75-ről 0,60-ra esik, az MRR
0,692-ről 0,454-re — utóbbi 34%-os relatív romlás. Nem semleges tehát, hanem
aktívan ront a találatokon.

### Ok

A pipeline két modellje nyelvi szempontból nem illik össze:

| Lépés | Modell | Nyelvi lefedettség |
|-------|--------|--------------------|
| Embedding | `text-embedding-3-small` (OpenAI) | többnyelvű — a magyar kérdést helyesen köti az angol recepthez (0,39) |
| Rerank | `cross-encoder/ms-marco-MiniLM-L-12-v2` (lokális) | **kizárólag angol** (MS MARCO passage ranking) |

A korpusz angol nyelvű, a felhasználói kérdés magyar. Az embedding modell ezt
áthidalja, a MiniLM viszont nem: magyar kérdésre nem tud értelmes relevancia-
pontszámot adni, ezért ad minden párra egyformán alacsony értéket.

### Miért nem blokkoló

A `RAGRequest.strategy` alapértelmezése `BASELINE`, tehát a `chunked_rerank`
opcionális, kísérleti ág, amit csak explicit kérésre kap a rendszer. A gyenge
reranker így nem befolyásolja a kiszolgált válaszokat.

### Lehetséges következő lépések

1. **Többnyelvű reranker** (pl. `BAAI/bge-reranker-v2-m3`). Kódváltoztatás nem
   kell, csak a `RERANKER_MODEL` környezeti változó és egy modellletöltés, utána
   újramérés a `rag_eval` harness-szel. Cserébe lényegesen nagyobb modell, tehát
   lassabb és memóriaigényesebb.
2. **Kérdés fordítása angolra** rerank előtt. Olcsóbb futásidőben, de egy extra
   LLM-hívás és egy újabb hibalehetőség a láncban.
3. **A stratégia elhagyása.** Ha a `chunked` önmagában elég jó, a rerank ág
   törölhető — kevesebb kód, kevesebb függőség (`sentence-transformers`, torch).

Döntés eddig: egyik sem, a `baseline` marad az alapértelmezés. A jelenség
dokumentált mérési eredmény, nem elfedett hiányosság.

---

## B-2 — Fázis 2/3 elmaradt tételek

Ezeket a `docs/phase-1-refactor.md` „Ami tudatosan kimaradt" szekciója sorolja
fel (indexelés összevonása, streaming, session management, `sources[]` a chat
válaszban). Itt szándékosan nem duplikálom őket, hogy ne csússzon szét a két
lista.

---

## B-3 — A rollback út nem azonos válaszokat ad

**Státusz:** nyitott, tudatosan vállalt
**Érintett kód:** `lib/chat/inlineRag.ts` kontra `rag_core/generation.py`
**Forrás:** `docs/phase-2-test-protocol.md`, M-2

Ugyanarra a kérdésre („Hogyan készül a hummus?") service módban 2140, inline
módban 2115 prompt token keletkezett. A TypeScript rollback tehát nem bájtazonos
mása a Python útnak — eltér a prompt összeállítása vagy a chunkok kezelése.

Következmény: amíg a rendszer inline módban fut, az eval-eredmények nem pontosan
a futó viselkedést írják le, mert az evalok a `rag_core`-t mérik. Rövid
vészhelyzetre ez elfogadható ár a rendelkezésre állásért, tartós működésre nem.

Lehetséges lépés: a különbség forrásának azonosítása a két prompt kiírásával,
majd az inline út igazítása — vagy annak elfogadása és dokumentálása, hogy a
rollback csak degradált módban működik.

---

## B-4 — A `RAG_BACKEND` csendben nyeli az elgépelést

**Státusz:** nyitott, apró
**Érintett kód:** `lib/ragConfig.ts`
**Forrás:** `docs/phase-2-test-protocol.md`, M-4

A kód csak a pontos `inline` értéket ismeri fel, minden más service módot jelent:

```ts
export const RAG_BACKEND =
  process.env.RAG_BACKEND === "inline" ? "inline" : "service";
```

A tesztelés kezdetén a `.env` a `services` értéket tartalmazta. Ez véletlenül
helyesen működött, de egy elgépelt `inlien` esetén a rendszer némán service
módban maradna, a tesztelő pedig arra jutna, hogy a rollback nem működik.

Lehetséges lépés: ismeretlen érték esetén figyelmeztetés a konzolra, vagy hiba
dobása induláskor.

---

## B-5 — A `rerank_score` nem jut el a webes felületig

**Státusz:** nyitott, apró
**Érintett kód:** `lib/chat/ragServiceClient.ts`
**Forrás:** `docs/phase-2-test-protocol.md`, M-5

A `RagServiceChunk` interfész és a `mapChunks` leképezés csak a `doc_id`,
`base_id`, `text` és `score` mezőt viszi tovább, így a `RetrievedChunk`-ba
frissen bevezetett `rerank_score` a chat válaszában nem jelenik meg. A FastAPI-n
keresztül a pontszám látható, tehát a mérésekhez rendelkezésre áll.

Akkor válik érdekessé, ha a `chunked_rerank` valaha alapértelmezetté válik
(lásd B-1), vagy ha a felületen meg akarjuk jeleníteni a találatok
megbízhatóságát.

---

## B-6 — Hibaágon pontatlan a session azonosító

**Státusz:** nyitott, apró
**Érintett kód:** `app/api/chat/route.ts`, `catch` ág
**Forrás:** `docs/phase-2-test-protocol.md`, M-6

A `catch` blokk mindig `prod-<requestId>` értéket logol session azonosítóként,
akkor is, ha a kérésben érkezett `sessionId`. A `try` ág ezzel szemben helyesen
megkülönbözteti a prod és az eval hívásokat.

Következmény: egy sikertelen eval-hívás nem kereshető vissza a saját session-je
alatt, ami épp a hibák elemzésekor hiányzik a legjobban. A javítás annyi, hogy a
`sessionId` a `try` blokk elé kerül, így a `catch` is látja.

---

## B-7 — A TypeScript és a Python oldal alapértelmezései eltérnek

**Státusz:** nyitott, fennálló eltérés
**Érintett kód:** `lib/ragConfig.ts`, `config.py`

A két oldal ugyanazokat a környezeti változókat olvassa, de más értékre esik
vissza, ha nincsenek beállítva:

| Beállítás | `lib/ragConfig.ts` | `config.py` |
|-----------|--------------------|-------------|
| `RAG_GENERATION_TEMPERATURE` | env, alapértelmezés **0,7** | env, alapértelmezés **0,2** |
| `RAG_TOP_K` | env, alapértelmezés 5 | **fixen 5**, env-ből nem állítható |

A hőmérséklet eltérése a súlyosabb: ha a `.env` nem tartalmaz explicit értéket,
akkor inline módban lényegesen szabadabban generál a rendszer, mint service
módban, ugyanarra a kérdésre. Semmi nem jelzi ezt, csak a válaszok minősége
ingadozik — ez a fajta néma konfigurációs eltérés a legnehezebben felderíthető.

A `RAG_TOP_K` fordított irányban okoz gondot: a TypeScript oldal a kérés
törzsében küldi a `top_k` értéket, amit a FastAPI elfogad. Ha valaki a `.env`-ben
`RAG_TOP_K=10`-et állít be, a webes felület tíz chunkkal fut, az evalok viszont
továbbra is öttel, mert a Python oldal nem olvassa a változót.

Fontos: ez akkor is fennáll, ha service módban futsz. A prompt, a hőmérséklet és
a modell ilyenkor a Python oldalról jön, de a `top_k`, a `strategy` és a fixen
beégetett `prompt_version: "prod"` a kérés törzsében érkezik a Next.js oldalról.

Lehetséges lépések: a `config.py`-ban a `RAG_TOP_K` env-ből olvasása, a két
alapértelmezés egyeztetése, és rövid távon minden lényeges érték explicit
felvétele a `.env`-be, hogy ne az alapértelmezéseken múljon az egyezés.

---

## B-8 — Hosszú válaszok levágódnak

**Státusz:** nyitott, felhasználót érintő
**Érintett kód:** `rag_core/generation.py` (67. sor), `lib/ragConfig.ts`
**Forrás:** `docs/phase-2-test-protocol.md` T-5b

A generálás fixen beégetett `max_completion_tokens=400` értékkel fut. Hosszú,
sok lépéses recepteknél ez kevés: a 18 prompt szintű tesztesetből kettő (q5 —
tarka dal, q7 — Pad See Ew) mondat közben megszakadt. A bíró a q7-nél észre is
vette: „az utolsó lépés azonban félbeszakadt".

Két probléma egyszerre. Egyrészt az érték túl alacsony egy receptasszisztenshez.
Másrészt a Python oldalon nem konfigurálható, miközben a TypeScript oldal
`RAG_MAX_COMPLETION_TOKENS` néven env-ből olvassa (alapértelmezés szintén 400) —
ez ugyanaz a mintázat, mint a B-7.

Lehetséges lépés: az érték kiemelése a `config.py`-ba env-ből olvasva, és a limit
emelése (800–1000) a hosszabb receptekhez.

---

## B-9 — Az összegző, korpuszra vonatkozó kérdések elbuknak a retrievalen

**Státusz:** nyitott
**Érintett kód:** `rag_core/retrieval.py` (a keresési stratégia egésze)
**Forrás:** `docs/phase-2-test-protocol.md` T-5b

A „Melyik receptben használunk csicseriborsót?" kérdésre a rendszer azt válaszolta,
hogy egyik receptben sem — miközben a korpuszban ott a `hummus`, aminek az első
összetevője a csicseriborsó. Ugyanez a futás a q2-ben helyesen fel is sorolta.

A hiba a retrievalnél van: a kérdés nem egy dokumentumra irányul, hanem a korpusz
egészére vonatkozó szűrés („melyik receptben van X"). Egy top-5 vektoros keresés
erre szerkezetileg alkalmatlan, mert nem tud számba venni, csak hasonlítani.

Fontos következmény, hogy ezt a **prompt szintű bíró nem veszi észre**: 5/5
pontot és „strong" hűséget adott rá, mert a modell hű volt a kapott kontextushoz.
A bíró nem látja a korpuszt, csak a kérdést és a választ. Retrieval-hibát tehát
csak a RAG szintű kiértékelés tud kimutatni — a két szint nem helyettesíti
egymást.

Lehetséges lépések: metaadat-alapú vagy kulcsszavas szűrés a vektoros keresés
mellé (hibrid retrieval), vagy az ilyen kérdéstípus tudatos kizárása a rendszer
hatóköréből, dokumentáltan.

---

## Megoldott tételek

### ✔ A reranker hibája esetén elveszett a kontextus

`rag_core/reranker.py` — ha a CrossEncoder kivételt dobott, a `rerank_chunks`
üres listát adott vissza, így a generálás **kontextus nélkül** futott le, és a
modell a saját tudásából válaszolt egy RAG rendszerben. A hibát a `finally` ág
logolta ugyan, de a hívó felé csendes maradt.

Javítva: a függvény hiba esetén visszaesik az eredeti pgvector sorrendre, és
törli az esetlegesen félbemaradt `rerank_score` értékeket, hogy részleges
pontozás ne kerüljön a válaszba. Rosszabb sorrendet adni még mindig jobb, mint
kontextus nélkül hagyni a generálást. Regressziós fedezet:
`tests/test_core.py::test_rerank_falls_back_to_vector_order_on_model_failure`.
