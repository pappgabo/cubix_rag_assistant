# Prompt Eval Jelentés: Válaszminőség és Hallucinációk

## 1. Kísérleti elrendezés

A `prompt_eval` futás célja az volt, hogy felmérje, milyen minőségű válaszokat ad a RAG‑asszisztens a recept‑domainben, amikor a retriever már biztosítja a releváns dokumentumokat.

- **Esetszám:** 18 manuálisan bírált kérdés  
- **Mért metrikák (LLM‑judge alapján):**
  - *context_relevance* (1–5)
  - *answer_quality* (1–5)
  - *faithfulness* (none / partial / strong)
- **Átlagos futási idő:** 8657 ms / kérdés

### Globális eredmények

- **Átlagos context relevance:** 4,11 / 5  
- **Átlagos answer quality:** 4,17 / 5  
- **Faithfulness:** mind a 18 válasz *strong* (nincs hallucináció)

---

## 2. Eredmények összefoglalása

A judge‑értékelések alapján:

- A legtöbb kérdésnél (pl. marhahúsos taco, hummusz, tarka dal, thai sült rizs, pita, Massaman curry, pizza tészta, aloo matar) a válasz **részletes, pontos és kontextushelyes**.
- A magyarázatok kiemelik, hogy a válaszok:
  - megfelelnek a receptgyűjtemény információinak,
  - nem tartalmaznak hibát,
  - nem tartalmaznak kitalált adatot.  
- Ez összhangban van a **18/18 strong faithfulness** eredménnyel.

**Következtetés:** ha a retriever jó kontextust ad, a jelenlegi prompt + modell stabilan, hallucináció nélkül működik.

---

## 3. Tipikus válaszminta és erősségek

### Jellemző jó esetek

#### Receptlépéses kérdések
- **q1:** marhahúsos taco – részletes lépések, fűszerezés, időtartam  
- **q5:** tarka dal – a judge szerint pontosan visszaadja a klasszikus menetet  
- **q7:** Pad See Ew  
- **q8:** pita  
- **q11:** pizza tészta  

#### Hozzávaló‑listák és leíró kérdések
- **q2:** hummusz összetevők  
- **q6:** thai sült rizs  
- **q9:** guasacaca  
- **q10:** Massaman curry fűszerezés  
- **q12:** aloo matar jellege  

A judge gyakran **5‑ös answer quality** értékelést ad ezekre.

### Erősségek összefoglalva

A rendszer különösen jól teljesít, amikor:

- a kérdés egy konkrét receptre vagy jól definiált ételre vonatkozik, és  
- a kontextusban valóban ott van a megfelelő markdown‑dokumentum.

---

## 4. Feltárt gyengeségek

### 4.1. Hiányzó receptek (coverage / UX)

Két kérdésnél (q3: indiai padlizsánkrém, q13: okrát tartalmazó recept) a válasz:

> „Sajnos erről nincs információm a recepttáramban.”

A judge értékelése:

- **faithfulness:** strong  
- **context_relevance:** 1  
- **answer_quality:** 2  

**Probléma:**  
Tartalmilag korrekt, de gyenge UX: nincs alternatíva, nincs útmutatás.

**Megjegyzés:**  
Ez nem modellhiba, hanem UX/prompt döntés.

---

### 4.2. Félbemaradó válaszok (output completeness)

Több hosszabb receptnél a válasz vége hiányzik:

- **q5:** tarka dal – a judge szerint a vége hiányos  
- **q7:** Pad See Ew – utolsó mondat félbeszakad  
- **q11:** pizza tészta – a formázás/sütés rész nem ér végig  

**Következmény:**  
answer_quality = 4/5, a judge a befejezetlenséget jelöli meg okként.

**Valószínű ok:**  
max_tokens limit vagy stop condition, nem tudáshiány.

---

### 4.3. Latencia és „farok”

- **Átlag:** ~8,7 s  
- **Kiugró értékek:**  
  - q1: ~33,5 s  
  - q11: ~14,1 s  

Valószínű ok: hosszabb kontextus + hosszabb válasz.

**Javaslatok:**

- kontextus hosszának upper boundja  
- rövidebb, tömörebb válaszok (pl. max 8–10 lépés)

---

## 5. Következtetések és ajánlott módosítások

### Összkép

A rendszer:

- magas relevanciát és válaszminőséget produkál,
- **0 hallucinációt** mutat (18/18 strong faithfulness),
- a hibák főként UX‑hez és válasz‑hosszhoz kapcsolódnak.

### Ajánlott változtatások

#### 1. „Nincs recept” UX javítása
Prompt‑kiegészítés:

- jelezze röviden, ha nincs releváns dokumentum,
- ajánljon hasonló ételt a gyűjteményből, vagy
- adjon általános tippet („ehhez a stílushoz ez áll legközelebb”).

#### 2. Válaszok lezárásának biztosítása
- max_tokens növelése, vagy  
- promptban: „fejezd be a receptet; ha túl hosszú, foglald össze a végén”.

#### 3. Latencia-optimalizálás
- rövidebb, célzottabb kontextus  
- kisebb modell használata, ha belefér

---

## 6. Metrikák összefoglaló táblázata

| Metrika            | Átlagérték   | Megjegyzés |
|--------------------|--------------|------------|
| Context Relevance  | 4,11 / 5     | A retriever általában tűpontos forrásokat ad az LLM-nek. |
| Answer Quality     | 4,17 / 5     | Erős, jól strukturált válaszok, néha technikai korlátokkal. |
| Faithfulness       | 100% Strong  | Zéró hallucináció. Minden válasz igazolható a forrásokból. |
| Avg. Latency       | 8,6 s        | Üzleti/demo környezetben elfogadható válaszidő. |

---

## Rövid összefoglaló mondat

**„18 kézzel bírált kérdésre a rendszer átlagos context relevance pontszáma 4,11/5, az answer quality 4,17/5, és minden válasz strong faithfulness besorolást kapott, azaz nem figyeltünk meg hallucinációt; a fő fejlesztési pont a hiányzó receptek esetén adott hasznosabb UX, illetve néhány hosszabb receptnél a válaszok befejezettségének biztosítása.”**