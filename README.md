# Recept RAG Asszisztens

RAG-alapú receptasszisztens **pgvector** + **OpenAI** stackkel, háromszintű offline eval rendszerrel és egységes LLM monitoringgal.

- **Prod path:** Next.js UI + `/api/chat` (proxy) → FastAPI `rag_service` → `rag_core`
- **Eval path:** Python batch scriptek (retrieval / prompt / conversation)
- **Promptok:** központi `prompts/` mappa
- **Dokumentáció:** `docs/phase-1-refactor.md`, `docs/phase-2-fastapi.md`

Repo: https://github.com/pappgabo/cubix_rag_assistant

---

## Architektúra

```text
┌─────────────────────────────────────────────────────────────┐
│ PROD (Next.js)                                              │
│  UI → POST /api/chat (proxy) → FastAPI rag_service          │
│       → rag_core.run_rag → pgvector + OpenAI                │
│  ingest.py → POST /api/upload-docs → pgvector index         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EVAL HARNESS (Python, offline)                              │
│  rag_eval        → retrieval metrikák (P@k, MRR, …)         │
│  prompt_eval     → Python RAG + LLM judge                   │
│  conversation_eval → HTTP hívás a prod /api/chat-re         │
└─────────────────────────────────────────────────────────────┘
```

| Eval szint | Mit mér | Mit hív |
|------------|---------|---------|
| `rag_eval` | Retrieval minőség | `rag_core` retrieval + PostgreSQL/pgvector (+ reranker) |
| `prompt_eval` | Generálás + judge | `rag_core` pipeline (`run_rag`) + `prompts/rag/system.txt` |
| `conversation_eval` | Multi-turn UX | **Prod** `/api/chat` + `prompts/rag/system.txt` |

A `prompt_eval` és a prod `/api/chat` **ugyanazt** a `system.txt` promptot és **ugyanazt**
a `rag_core.run_rag` pipeline-t használja (service módban), így a prompt eval valódi
regressziót mér a prod viselkedésen.

---

## RAG service (`rag_service`)

A prod chat alapértelmezetten a Python FastAPI service-t hívja — nem másolja a RAG-logikát TypeScriptben.

| Endpoint | Feladat |
|----------|---------|
| `GET /health` | Service él-e |
| `POST /v1/rag/query` | `RAGRequest` → `run_rag` → `RAGResponse` |

Indítás: `uv run uvicorn rag_service.main:app --port 8000 --reload`

OpenAPI: http://localhost:8000/docs

A Next.js `/api/chat` vékony proxy: session-drótozás, FastAPI hívás, **TS safety filter**, `{ ok, answer, sources }` válasz.

Rollback (service nélkül): `RAG_BACKEND=inline` — régi TS retrieval + OpenAI (`lib/chat/inlineRag.ts`).

---

## TypeScript modulok (prod)

| Modul | Feladat |
|-------|---------|
| `app/api/chat/route.ts` | Proxy orchestrátor |
| `lib/chat/ragServiceClient.ts` | FastAPI kliens |
| `lib/chat/safetyFilter.ts` | Prod biztonsági szűrő |
| `lib/ragConfig.ts` | Közös env-kulcsok (temp, strategy, service URL) |
| `lib/vectorstore/pgvector.ts` | **Ingest only** (`/api/upload-docs`); `search()` csak inline rollback |

---

## RAG adatmodell (`rag_core`)

A korábban több helyen duplikált RAG-logika egyetlen csomagba, a `rag_core`-ba
került. Ez a kanonikus mag: az eval harness **és** a prod FastAPI service ezt hívja.

| Modul | Feladat |
|-------|---------|
| `rag_core/types.py` | `RAGRequest`, `RAGResponse`, `RetrievedChunk`, `RetrievalStrategy` (Pydantic) |
| `rag_core/retrieval.py` | Kanonikus embedding + pgvector keresés + `retrieve()` |
| `rag_core/reranker.py` | CrossEncoder reranker (lusta betöltés) |
| `rag_core/generation.py` | Prompt betöltés + OpenAI chat + egységes logolás |
| `rag_core/pipeline.py` | `run_rag(RAGRequest) -> RAGResponse` (retrieve + generate) |

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

## Prompt életciklus

- **Élő (prod):** `prompts/rag/system.txt` + `prompts/rag/user.template.txt`.
  Ezt használja a prod `/api/chat` és alapból a `prompt_eval` is.
- **Kísérleti verziók:** `prompts/rag/experiments/<verzió>.txt`.
  Eval alatt `RAGRequest.prompt_version="<verzió>"` értékkel mérhető.
- **Promotálás:** ha egy kísérleti prompt jobban teljesít, a tartalma átkerül a
  `system.txt`-be — így a prod és az eval nem csúszhat szét.

| Fájl | Használja |
|------|-----------|
| `prompts/rag/system.txt` | `rag_core` (prod service) + prompt eval |
| `prompts/rag/user.template.txt` | `rag_core` (prod service) + prompt eval |
| `prompts/rag/experiments/system.friendly.txt` | Kísérleti RAG system prompt |
| `prompts/eval/prompt_judge_*.txt` | Prompt-level LLM judge |
| `prompts/eval/conversation_judge_system.txt` | Multi-turn judge |
| `prompts/simulation/user_system.template.txt` | Szimulált user LLM |

---

## Követelmények

- Node.js 20+
- Python 3.12 ([uv](https://docs.astral.sh/uv/) ajánlott — lásd `.python-version`)
- Docker (PostgreSQL + pgvector)
- OpenAI API kulcs

---

## Gyors indítás

### 1. Környezeti változók

A titkokat a projekt gyökerében lévő **`.env`** fájl tárolja (gitignore-olva). A repóban
van egy `.env.example` sablon — másold `.env`-be és töltsd ki:

```bash
cp .env.example .env          # macOS/Linux
Copy-Item .env.example .env   # Windows PowerShell
```

> **Miért `.env` és nem `.env.local`?** A Python oldal (`config.py` → `load_dotenv()`)
> a **`.env`**-et olvassa, a Next.js pedig a `.env`-et **és** a `.env.local`-t is betölti.
> Egyetlen `.env` a gyökérben tehát **mindkét oldalt** kiszolgálja (Python eval + `rag_service` + Next.js).
> Ha csak `.env.local`-t hozol létre, a Next.js működik, de a Python eval „OPENAI_API_KEY nincs beállítva" hibával elszáll.

A `.env` tartalma (lásd `.env.example`):

```env
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4.1-mini

# RAG runtime (Python rag_core + Next.js /api/chat)
RAG_GENERATION_TEMPERATURE=0.7
RAG_MAX_COMPLETION_TOKENS=400
RAG_STRATEGY=baseline
RAG_TOP_K=5

# FastAPI RAG service (Fázis 2 — default backend; inline = service nélkül)
RAG_SERVICE_URL=http://localhost:8000
RAG_BACKEND=service

PGHOST=localhost
PGPORT=5432
PGDATABASE=ragdb
PGUSER=raguser
PGPASSWORD=ragpass
```

### 2. PostgreSQL + pgvector

```bash
docker run -d \
  --name pgvector \
  -e POSTGRES_USER=raguser \
  -e POSTGRES_PASSWORD=ragpass \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  ankane/pgvector
```

Inicializáld a táblákat (egyszeri):

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents_baseline (
    doc_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(1536)
);

CREATE TABLE IF NOT EXISTS documents_chunks (
    doc_id TEXT PRIMARY KEY,
    base_id TEXT NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(1536),
    FOREIGN KEY (base_id) REFERENCES documents_baseline(doc_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_documents_baseline_embedding
    ON documents_baseline USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_documents_chunks_embedding
    ON documents_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 3. Python függőségek (uv)

```bash
uv sync --group dev
uv run pytest
```

### 4. Next.js + RAG service

**Terminal 1 — FastAPI (rag_core):**

```bash
uv run uvicorn rag_service.main:app --port 8000 --reload
```

**Terminal 2 — Next.js:**

```bash
npm install
npm run dev
```

App: http://localhost:3000

Rollback a régi TS útra (service nélkül): `RAG_BACKEND=inline` a `.env`-ben.

### 5. Ingest

Indítsd a Next.js dev szervert, majd:

```bash
uv run python -m ingestion.ingest
uv run python -m ingestion.ingest_chunk
```

Adatforrás: [Jeff Thompson Recipes](https://github.com/jeffThompson/Recipes) (`data/` mappa).

---

## Eval futtatás

```bash
# RAG retrieval metrikák
uv run python -m rag_eval.run_rag_eval

# Prompt-level eval (Python RAG path)
uv run python -m prompt_eval.run_prompt_eval

# Multi-turn szimuláció (prod API-t hívja — Next.js ÉS rag_service fusson!)
uv run python -m conversation_eval.run_conversation_simulation
uv run python -m conversation_eval.judge_eval
```

| Modul | Input | Output |
|-------|-------|--------|
| RAG eval | `rag_eval/rag_tests.json` | `rag_eval/rag_results.json`, `rag_eval/eval_result.md` |
| Prompt eval | `prompt_eval/prompt_tests.json` | `prompt_eval/prompt_eval_results.json` |
| Conversation | `conversation_eval/batch_config.yaml` | `outputs/conversations.json`, `outputs/judge_results.json` |

---

## Monitoring

Minden LLM hívás log: `logs/llm-usage.log`

| Komponens | Forrás |
|-----------|--------|
| `rag-embed`, `rag-response` | Python `rag_core` (prod service + eval) |
| `chat-proxy`, `eval-chat-proxy` | Next.js proxy (latencia) |
| `rag-embed` (ingest) | `pgvector.ts` indexeléskor |

```bash
uv run python -m monitoring.summarize_llm_usage
```

---

## Chat API

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Hogyan készül a hummus?"}'
```

Válasz:

```json
{
  "ok": true,
  "answer": "...",
  "sources": [{ "docId": "hummus", "baseId": "hummus", "text": "...", "score": 0.92 }]
}
```

---

## Tesztek

```bash
uv run pytest
```

Unit tesztek: RAG metrikák, prompt fájlok, config defaultok, FastAPI service (mockolt `run_rag`). Integrációs tesztek (DB, OpenAI, end-to-end chat) manuálisan / CI-ben külön.

---

## Demó videók

1. [Technikai bemutató](https://www.loom.com/share/c573bb8b402c4804ab3ada2cea45dd24)
2. [Felhasználói demo](https://www.loom.com/share/2a98a749d13e46a9881ddccd73519d39)
