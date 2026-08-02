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
