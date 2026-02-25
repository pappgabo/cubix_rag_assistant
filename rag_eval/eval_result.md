# Elemzési Jelentés: RAG Retriever Teljesítményvizsgálat

## 1. Kísérleti elrendezés

A projekt során egy receptgyűjteményre épülő RAG (Retrieval-Augmented Generation) rendszer visszakeresési egységét teszteltük.  
A cél a dokumentum-alapú alapkeresés, a feldarabolt (chunking) és az újrarangsorolt (reranking) módszerek összehasonlítása volt.

### Metrikák (Top-5 találat alapján)

- **Precision@k** – A releváns találatok aránya a top-k listában.  
- **Recall@k** – A releváns dokumentumok mekkora részét sikerült előhívni.  
- **Hit@k** – Annak valószínűsége, hogy a top-k találat tartalmaz legalább egy jó választ.  
- **MRR@k (Mean Reciprocal Rank)** – Azt méri, milyen előkelő helyen szerepel az első jó találat.  
- **F1@k** – A precision és recall harmonikus átlaga.

### Tesztkészlet és Pipeline-ok

A vizsgálatot egy **22 kérdésből** álló készleten végeztük, amelyből **20 kérdéshez** tartozott definiált helyes válasz (Ground Truth).

- **documents_baseline** – Teljes dokumentum-szintű keresés  
- **documents_chunks** – Szemantikai darabolást (chunking) alkalmazó keresés  
- **chunked_rerank** – Darabolt keresés + *ms-marco-MiniLM-L-12-v2* reranker modell  

---

## 2. Összefoglaló metrikák

A mérések az alábbi átlagolt eredményeket hozták (a 20 GT esettel számolva):

| Pipeline            | Precision@5 | Recall@5 | Hit@5 | MRR@5 | F1@5 |
|---------------------|-------------|----------|-------|-------|------|
| **Baseline**        | 0.18        | 0.66     | 0.75  | 0.69  | 0.26 |
| **Chunks**          | 0.18        | 0.66     | 0.75  | 0.70  | 0.26 |
| **Chunks + Rerank** | 0.13        | 0.51     | 0.60  | 0.45  | 0.18 |

---

## 3. Eredmények értelmezése

### Baseline vs. Chunks

A chunking **nem hozott érdemi javulást**, ami két okra vezethető vissza:

1. **Dokumentum-karakterisztika**  
   A receptgyűjtemény eleve rövid, fókuszált dokumentumokból áll, ahol egy kérdésre jellemzően egy egész dokumentum a válasz.

2. **Granularitás**  
   A tesztkészlet kérdéseihez (pl. *„Hogyan készítsek tacót?”*) nincs szükség finomabb felbontásra; a dokumentum-szintű keresés elegendő kontextust ad.

---

### A Reranker hatása és a „Config Mixing” anomália

A reranker bevezetése **jelentős teljesítményromlást** okozott:

- **Hit rate**: 0.75 → 0.60  
- **Recall**: 0.66 → 0.51  

#### Okok:

- **Nyelvi aszimmetria**  
  A használt *ms-marco* modell angol nyelvű.  
  A magyar kérdések és az angol kontextus közötti szemantikai kapcsolatot nem tudta megfelelően kezelni.

- **Negatív rangsorolás**  
  A naplófájlok alapján a reranker **szisztematikusan hátrasorolta** a releváns találatokat  
  (gyakran mélyen negatív score-t adva nekik), így azok kiestek a Top-5-ből.

---

### Komplex kérdések kihívásai

A „halmaz” típusú kérdések (pl. *thai ételek*, *saláták listázása*) rávilágítottak, hogy:

- a fix **k = 5** korlát mellett a Recall nehezebben maximalizálható,  
- mivel ezekhez **több mint 5 releváns dokumentum** is tartozhat a gyűjteményben.

---

## 4. Következtetések és ajánlás

A jelenlegi konfigurációban **nem javasolt** a *chunking + rerank* pipeline élesítése.

A komplexebb rendszer:

- **lassabb** (~6–8s latencia),  
- **pontatlanabb**,  
- és a nyelvi inkonzisztencia miatt **szisztematikusan rontja** a találati pontosságot.

### Összegző állítás

> **„A vizsgált recept-domainen a dokumentum-szintű baseline retriever már magas (≈0.66–0.72) recall@5-öt ér el.  
> A reranker konfiguráció a nyelvi inkonzisztencia (angol modell – magyar kérdések) miatt kifejezetten ront a hatékonyságon, ezért alkalmazása ellenjavallt.”**

---

## 5. További fejlesztési irányok (Future Work)

- **Hibrid keresés (Hybrid Retrieval)**  
  Vektoros keresés kombinálása BM25-tel, hogy a specifikus kifejezések (pl. „pita”, „taco”) ne vesszenek el.

- **Multilingual Reranker**  
  Natívan többnyelvű modell (pl. *BGE-M3*) használata a nyelvi gátak áthidalására.

- **Dinamikus Top-k**  
  A visszakért dokumentumok számának növelése a reranker számára, hogy a halmaz-típusú kérdéseknél jobb Recall-t érjünk el.