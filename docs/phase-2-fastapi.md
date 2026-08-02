# Fázis 2 — FastAPI façade (prod = eval kódúton)

> Összefoglaló a Fázis 2 (PR1–PR4) változásairól. Használható MR-leírásként és csapaton belüli átadó dokumentumként.

## TL;DR

- Bevezettük a **`rag_service`** FastAPI appot: `POST /v1/rag/query` → `rag_core.run_rag`.
- A prod **`/api/chat` vékony TS proxy** lett: session-drótozás + safety filter maradt Next.js-ben.
- **Egységes runtime config** (temp 0.7, strategy, top_k, max_tokens) Python + TS env-kulcsokon.
- Chat válasz bővült: `{ ok, answer, sources[] }` — visszafelé kompatibilis a conversation eval-lal.
- **`lib/vectorstore/pgvector.ts`** megmaradt **csak ingest/upload-docs** célra; a prod chat alapértelmezetten nem hívja.

---

## Előtte → Utána

### Architektúra

| | Fázis 1 után | Fázis 2 után |
|--|--------------|--------------|
| Prod retrieval | `lib/vectorstore/pgvector.ts` (TS) | `rag_core.retrieval` (Python, service-en keresztül) |
| Prod generation | TS OpenAI hívás | `rag_core.generation` (Python) |
| Prod prompt | `prompts/rag/system.txt` (TS olvassa) | ugyanaz, de Python tölti be |
| Eval prompt_eval | `rag_core.run_rag` | változatlan |
| conversation_eval | `/api/chat` HTTP | változatlan interfész (`answer` mező) |
| Duplikáció | TS + Python retrieval | **egy futó igazságforrás** (service mód) |

### Kérésfolyam (prod, default)

```text
Böngésző / conversation_eval
   │  POST /api/chat { question, sessionId? }
   ▼
Next.js proxy (app/api/chat/route.ts)
   │  sessionId drótozás (prod- vs eval-chat)
   │  POST RAG_SERVICE_URL/v1/rag/query
   ▼
FastAPI rag_service/main.py
   │  run_rag(RAGRequest) → RAGResponse
   ▼
rag_core (retrieval + generation + logolás)
   │
   ▼
TS proxy: applySafetyFilter(answer)
   │
   ▼
{ ok, answer, sources[] }
```

---

## PR-bontás (implementált)

| PR | Tartalom |
|----|----------|
| **PR1** | `rag_service/main.py`, FastAPI deps, `tests/test_rag_service.py` |
| **PR2** | Config unifikáció: temp **0.7**, `RAG_MAX_COMPLETION_TOKENS`, `RAG_STRATEGY`, `RAG_TOP_K` |
| **PR3** | `/api/chat` proxy átállás, `sources[]`, `RAG_BACKEND=service\|inline` rollback |
| **PR4** | Dokumentáció, `pgvector.ts` szerep tisztázása |

---

## Új / módosított fájlok

### Hozzáadva
- `rag_service/__init__.py`, `rag_service/main.py`
- `lib/chat/ragServiceClient.ts` — FastAPI kliens
- `lib/chat/inlineRag.ts` — rollback útvonal (`RAG_BACKEND=inline`)
- `lib/chat/safetyFilter.ts` — prod safety filter (TS-ben maradt)
- `lib/chat/types.ts` — `RagSource`, `RagQueryResult`
- `lib/ragConfig.ts` — közös env-kulcsok + `RAG_SERVICE_URL`, `RAG_BACKEND`
- `tests/test_rag_service.py`

### Módosítva
- `app/api/chat/route.ts` — vékony orchestrátor (proxy / inline)
- `config.py` — temp 0.7, max_tokens, strategy validáció
- `rag_core/generation.py`, `rag_core/types.py` — config-driven defaultok
- `pyproject.toml` — `fastapi`, `uvicorn[standard]`
- `README.md` — friss architektúra, env, indítás
- `lib/vectorstore/pgvector.ts` — fejléc: ingest-only prod path

---

## API kontraktus

### FastAPI — `POST /v1/rag/query`

Bemenet: `RAGRequest` (Pydantic, snake_case JSON)

```json
{
  "question": "Hogyan készül a hummus?",
  "session_id": "prod-…",
  "request_id": "…",
  "top_k": 5,
  "strategy": "baseline",
  "prompt_version": "prod"
}
```

Kimenet: `RAGResponse`

```json
{
  "answer": "…",
  "chunks": [{ "doc_id", "base_id", "text", "score", "metadata" }],
  "strategy": "baseline",
  "model": "gpt-4.1-mini",
  "prompt_version": "prod"
}
```

OpenAPI docs: `http://localhost:8000/docs`

### Next.js — `POST /api/chat`

Bemenet (változatlan):

```json
{ "question": "…", "sessionId": "…" }
```

Kimenet:

```json
{
  "ok": true,
  "answer": "…",
  "sources": [{ "docId", "baseId", "text", "score" }]
}
```

---

## Döntések (Fázis 2)

| Kérdés | Döntés |
|--------|--------|
| Temperature | **0.7** (prod-konzisztencia) |
| Safety filter | **TS proxyban** marad |
| `pgvector.ts` | **Megmarad** ingest/upload-docs miatt; chat nem hívja (service mód) |
| Rollback | `RAG_BACKEND=inline` — régi TS retrieval + OpenAI |

---

## Környezeti változók

| Kulcs | Default | Hol |
|-------|---------|-----|
| `RAG_SERVICE_URL` | `http://localhost:8000` | Next.js |
| `RAG_BACKEND` | `service` | Next.js (`inline` = rollback) |
| `RAG_GENERATION_TEMPERATURE` | `0.7` | Python + inline TS |
| `RAG_MAX_COMPLETION_TOKENS` | `400` | Python + inline TS |
| `RAG_STRATEGY` | `baseline` | Python (+ inline TS; rerank csak Pythonban) |
| `RAG_TOP_K` | `5` | Python + TS |

---

## Logolás

| Komponens | Mikor |
|-----------|-------|
| `rag-embed`, `rag-response` | Python `rag_core` (service mód) |
| `chat-proxy`, `eval-chat-proxy` | TS proxy (latencia, siker/hiba) |
| `chat`, `eval-chat` | TS inline rollback mód |
| `rag-embed` (ingest) | `pgvector.ts` indexeléskor |

---

## Futtatás

```bash
# Terminal 1
uv run uvicorn rag_service.main:app --port 8000 --reload

# Terminal 2
npm run dev
```

A `conversation_eval` a prod `/api/chat`-et hívja → **mindkét service** kell (Next.js + FastAPI).

---

## Ami szándékosan kimaradt (későbbi fázis)

- Indexelés összevonása (`ingest.py` vs `/api/upload-docs`)
- `chunked_rerank` prod-ba kapcsolása (rag_eval számok alapján)
- Streaming válasz a chatben
- `pgvector.ts` teljes nyugdíjazása (Python ingest felé)

---

## Ellenőrzés

```bash
uv sync --group dev
uv run pytest

# Service health
curl http://localhost:8000/health

# End-to-end (Next.js + service fut)
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Hogyan készül a hummus?"}'
```
