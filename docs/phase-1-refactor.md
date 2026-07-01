# Fázis 1 — Kanonikus RAG mag (`rag_core`)

> Ez a dokumentum összefoglalja, mi változott a Fázis 1 során a korábbi állapothoz
> képest. Használható MR-leírásként és csapaton belüli átadó dokumentumként.

## TL;DR

- Bevezettük a **`rag_core`** csomagot: **egy** retrieval + generation + pipeline
  implementáció, közös **RAG adatmodellel** (`RAGRequest` / `RAGResponse`).
- Megszűnt a **duplikált Python RAG-logika** (`rag_app/` törölve).
- Egységes **prompt életciklus**: egyetlen élő `system.txt` (prod = eval), a
  kísérleti promptok `prompts/rag/experiments/` alá kerültek.
- A `prompt_eval` mostantól **ugyanazt a promptot és pipeline-t** méri, mint a prod.
- Bővített teszt-lefedettség, minden zöld (`uv run pytest`).

A **chat ⟷ eval runtime szétválasztás megmaradt**: a prod Next.js UI és az offline
eval harness továbbra is külön fut.

---

## Miért volt rá szükség

Korábban **három párhuzamos RAG-út** létezett, kissé eltérő viselkedéssel:

```text
RETRIEVAL (3×)
├── lib/vectorstore/pgvector.ts            → prod, TS
├── rag_eval/retrieval.py                  → eval metrikák, Python
└── rag_app/retrieval_for_prompt_eval.py   → wrapper a fentire

GENERATION (2×)
├── app/api/chat/route.ts                  → prod prompt
└── rag_app/generate_response.py           → eval prompt (más!)
```

Ebből fakadt, hogy a **prompt eval nem azt mérte, ami prodban futott** (külön
system prompt, külön generálási kód). A Fázis 1 célja: **egy igazságforrás**
retrieval + generation szinten, a runtime-szétválasztás megtartása mellett.

---

## Előtte → Utána

### Architektúra

| | Előtte | Utána |
|--|--------|-------|
| Python retrieval | `rag_eval/retrieval.py` + `rag_app/…` | `rag_core/retrieval.py` (egy forrás) |
| Python generation | `rag_app/generate_response.py` | `rag_core/generation.py` |
| RAG adatmodell | nincs (ad-hoc dict-ek) | `rag_core/types.py` (Pydantic) |
| Prompt eval hívása | saját retrieve + generate | `rag_core.pipeline.run_rag` |
| RAG system prompt | `system.prod.txt` ≠ `system.eval.txt` | egyetlen `system.txt` + `experiments/` |
| User template | `user.template.txt` (`{query}/{documents}`) + `user.prod.template.txt` | egy `user.template.txt` (`{question}/{context}`) |

### Új `rag_core` csomag

| Modul | Feladat |
|-------|---------|
| `rag_core/types.py` | `RAGRequest`, `RAGResponse`, `RetrievedChunk`, `RetrievalStrategy` |
| `rag_core/prompts.py` | prompt-verzió feloldás (`prod` → `system.txt`, egyéb → `experiments/<v>.txt`) |
| `rag_core/retrieval.py` | `embed_text`, `search_pgvector`, `retrieve(request)` |
| `rag_core/reranker.py` | CrossEncoder reranker (lusta modellbetöltés) |
| `rag_core/generation.py` | prompt betöltés + OpenAI chat + egységes logolás |
| `rag_core/pipeline.py` | `run_rag(RAGRequest) -> RAGResponse` |

---

## Részletes változáslista

### Hozzáadva
- `rag_core/` csomag (`__init__.py`, `types.py`, `prompts.py`, `retrieval.py`,
  `reranker.py`, `generation.py`, `pipeline.py`).
- `prompts/rag/system.txt` — egyetlen élő RAG system prompt.
- `prompts/rag/experiments/system.friendly.txt` — a korábbi eval prompt kísérleti verzióként megőrizve.
- Új/​bővített tesztek a `tests/test_core.py`-ban (rag_core adatmodell, prompt-feloldás, egyesített placeholderek).

### Módosítva
- `config.py` — új prompt path-ek (`RAG_SYSTEM_PROMPT_PATH`, `RAG_USER_PROMPT_PATH`,
  `RAG_EXPERIMENTS_DIR`), és új RAG beállítások (`RAG_CHAT_MODEL`,
  `RAG_GENERATION_TEMPERATURE`, `RAG_CANDIDATE_MULTIPLIER`).
- `prompt_eval/eval_engine.py` — `run_rag` pipeline-t hív a régi `rag_app` helyett;
  `prompt_version` paraméter végigvezetve.
- `rag_eval/retrieval.py` — a low-level retrieval a `rag_core`-ból jön; itt már csak
  az eval-specifikus glue (teszteset-betöltés, base_id dedup a metrikákhoz).
- `rag_eval/reranker.py` — vékony re-export a `rag_core.reranker`-ből (backward compat).
- `app/api/chat/route.ts` — az egyesített `system.txt` / `user.template.txt` promptokat tölti.
- `prompts/rag/user.template.txt` — egységes `{question}` / `{context}` placeholderek.
- `README.md` — új „RAG adatmodell" és „Prompt életciklus" szekció, frissített eval/prompt táblák.
- `pyproject.toml` — `requires-python = ">=3.12"` (a `.python-version`-nal egyeztetve),
  duplikált dev-függőség kitakarítva.

### Törölve
- `rag_app/` (mind a `generate_response.py`, mind a `retrieval_for_prompt_eval.py`) —
  a logika átkerült a `rag_core`-ba.
- `prompts/rag/system.prod.txt`, `prompts/rag/system.eval.txt`,
  `prompts/rag/user.prod.template.txt` — összevonva / kísérletbe áthelyezve.

---

## Prompt életciklus (új modell)

- **Élő (prod):** `prompts/rag/system.txt` + `prompts/rag/user.template.txt`.
  Ezt használja a prod `/api/chat` **és** alapból a `prompt_eval` is.
- **Kísérleti verziók:** `prompts/rag/experiments/<verzió>.txt`.
  Eval alatt `RAGRequest.prompt_version="<verzió>"` értékkel mérhető.
- **Promotálás:** ha egy kísérleti prompt jobban teljesít, a tartalma átkerül a
  `system.txt`-be — így a prod és az eval nem csúszhat szét.

---

## RAG adatmodell — használat

```python
from rag_core.pipeline import run_rag
from rag_core.types import RAGRequest, RetrievalStrategy

resp = run_rag(RAGRequest(
    question="Hogyan készül a hummus?",
    session_id="demo",
    strategy=RetrievalStrategy.BASELINE,   # baseline | chunked | chunked_rerank
    prompt_version="prod",                  # prod | <kísérleti verzió neve>
))
print(resp.answer)
print([c.base_id for c in resp.chunks])
```

---

## Breaking changes / migrációs megjegyzések

- **`rag_app` megszűnt.** Aki `from rag_app.generate_response import generate_response`
  vagy `retrieve_docs_for_question` importot használt, váltson erre:
  `from rag_core.pipeline import run_rag` (`RAGRequest` bemenettel).
- **Prompt path-ek átnevezve.** A régi `RAG_SYSTEM_PROD_PROMPT_PATH` /
  `RAG_SYSTEM_EVAL_PROMPT_PATH` / `RAG_USER_PROD_PROMPT_PATH` konstansok megszűntek;
  helyettük `RAG_SYSTEM_PROMPT_PATH`, `RAG_USER_PROMPT_PATH`, `RAG_EXPERIMENTS_DIR`.
- **User template placeholderek** `{query}`/`{documents}` → `{question}`/`{context}`.
- **Python 3.12** az elvárt minimum (lásd `.python-version`, `pyproject.toml`).
- `rag_eval` és `run_rag_eval` publikus felülete **változatlan** — a re-exportok miatt
  a meglévő eval scriptek átírás nélkül futnak.

---

## Ellenőrzés

```bash
uv sync --group dev
uv run pytest            # tesztek zöld
```

Import-smoke (körkörös import / szintaxis kiszűrésére):

```bash
uv run python -c "import rag_core.pipeline, prompt_eval.eval_engine, rag_eval.run_rag_eval; print('OK')"
```

---

## Ami tudatosan kimaradt (Fázis 2)

- A prod `/api/chat` átállítása a `rag_core`-ra (FastAPI façade) — a TS oldal
  egyelőre saját retrievallel „tükrözi" a contractot.
- Retrieval stratégia configból prodban, `sources[]` a chat válaszban.
- Indexelés (`ingest` vs `/api/upload-docs`) összevonása, streaming.
