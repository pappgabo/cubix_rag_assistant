# 🧠 AI Recept Asszisztens – Telepítési és Használati Útmutató

Ez a dokumentum végigvezet a rendszer teljes telepítésén, konfigurálásán és futtatásán.  
A projekt egy RAG (Retrieval-Augmented Generation) alapú receptasszisztens:

- Next.js frontend + backend
- PostgreSQL + pgvector vektortár
- OpenAI embedding + chat modellek
- Python ingest pipeline
- Többszintű evaluációs modulok

A kód elérhető: https://github.com/pappgabo/cubix_rag_assistant
---

# 1. Rendszerkövetelmények

A projekt futtatásához szükséges:

- **Node.js 20+**
- **Python 3.10+**
- **Docker + Docker Compose**
- **OpenAI API kulcs**
- **Git**

---

# 2. Környezeti változók

Hozd létre a `.env.local` fájlt a projekt gyökerében:
```bash
    OPENAI_API_KEY=ide_írd_az_api_kulcsot
    EMBEDDING_MODEL=text-embedding-3-small
    CHAT_MODEL=gpt-4.1-mini

    PGHOST=localhost
    PGPORT=5432
    PGDATABASE=pl.: ragdb
    PGUSER=pl.: raguser
    PGPASSWORD=pl.: ragpass
```

# 3. PostgreSQL + pgvector indítása Dockerben

A projekt PostgreSQL-t használ pgvector kiterjesztéssel.  
Indítsd el a konténert:

```bash
docker run -d \
  --name pgvector \
  -e POSTGRES_USER=raguser \
  -e POSTGRES_PASSWORD=ragpass \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  ankane/pgvector
```

# 4. Automatikus adatbázis inicializálás (táblák + indexek)
Hozz létre egy fájlt:

    docker/init/01-init.sql
    Tartalma:
```bash 
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS documents_baseline (
        doc_id TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        metadata JSONB,
        embedding VECTOR(1536));

    CREATE TABLE IF NOT EXISTS documents_chunks (
        doc_id TEXT PRIMARY KEY,
        base_id TEXT NOT NULL,
        text TEXT NOT NULL,
        metadata JSONB,
        embedding VECTOR(1536),
        FOREIGN KEY (base_id) REFERENCES documents_baseline(doc_id) ON DELETE CASCADE);

    CREATE INDEX IF NOT EXISTS idx_documents_baseline_embedding
        ON documents_baseline
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);

    CREATE INDEX IF NOT EXISTS idx_documents_chunks_embedding
        ON documents_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
```
# 5. Docker Compose használata 
Hozd létre:

docker/docker-compose.yml
```bash
version: "3.9"

services:
  pgvector:
    image: ankane/pgvector
    container_name: pgvector
    restart: always
    environment:
      POSTGRES_USER: raguser
      POSTGRES_PASSWORD: ragpass
      POSTGRES_DB: ragdb
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init:/docker-entrypoint-initdb.d

volumes:
  pgdata:
```

Indítás:
docker compose -f docker/docker-compose.yml up -d

# 6. Next.js telepítése és futtatása
## 6.1 Dependency-k telepítése
```bash
npm install
```
## 6.2 Fejlesztői szerver indítása
```bash
npm run dev
```

# 7. Dokumentumok feltöltése (Ingest Pipeline)
A feladathoz adatforrásnak:Jeff Thompson's Recipes-egyszerű markdown formátumú receptjeit használtam (https://github.com/jeffThompson/Recipes). Ezeket a data mappában töltöttem le.
A Python ingest.py script beolvassa a data/ mappát és feltölti a dokumentumokat a backendnek.             

```bash
python -m ingestion/ingest
python -m ingestion/ingest_chunk 
```
Ez:
- normalizálja a dokumentumokat,
- chunkolja őket,
- embeddinget generál,
- feltölti a pgvector adatbázisba.

# 8. Ellenőrzés PostgreSQL-ben
Lépj be a konténerbe:
```bash
docker exec -it pgvector psql -U raguser -d ragdb
```

Ellenőrizd:
```bash
SELECT COUNT(*) FROM documents_baseline;
SELECT COUNT(*) FROM documents_chunks;
```
# 9. RAG Chat használata
A frontend chat UI automatikusan hívja a backend /api/chat endpointot:
- embedding generálás
- releváns chunkok keresése
- RAG válasz generálása
- streaming visszaküldése a böngészőbe
A webapp elérhető: http://localhost:3000

# 10. Evaluációs modulok futtatása
## 10.0 Python modul követelmények a rootban a requirements.txt-ben vannak
## 10.1 RAG-szintű értékelés
```bash
python -m rag_eval/run_rag_eval
```
goldenset: rag_eval/rag_tests.json
Eredmény: rag_eval/rag_results.json
Evaluation eredmény: rag_eval/eval_result.md

## 10.2 Prompt-szintű értékelés
```bash
python -m prompt_eval/run_prompt_eval
```
input questions: prompt_eval/prompt_tests.json
Eredmény: prompt_eval/prompt_eval_results.json
Evaluation eredmény: prompt_eval/eval_result.md

## 10.3 Multi-turn értékelés
```bash
python -m conversation_eval/run_conversation_simulator
python -m conversation_eval/judge_eval    
```
Szimuláció: outputs/conversations.json
Eredmény: output/judge_results.json
Evaluation eredmény: conversation_eval/conversation_eval.md

# 11. Logolás és monitoring
Minden LLM hívás logolva van:

timestamp
sessionId
requestID
model
tokenhasználat
költség
latency

```bash
[LLM_USAGE] {"timestamp": "2026-02-22T18:54:40.496473Z", "sessionId": "rag-eval-20260222-195437", "requestId": "req-q2-ac39fa54", "component": "rag-embed", "model": "text-embedding-3-small", "provider": "openai", "promptTokens": 18, "completionTokens": 0, "totalTokens": 18, "costUsd": 3.6e-07, "latencyMs": 1026, "success": true, "errorMessage": null}
```
A logfájl a következő helyen található:
logs/llm-usage.log

Összefoglaló riport generáló: 
```bash
python -m monitoring.summarize_llm_usage
```

# 12. Videó demók:

1. VIDEÓ -TECHNIKAI BEMUTATÓ: https://www.loom.com/share/c573bb8b402c4804ab3ada2cea45dd24

2. VIDEÓ -FELHASZNÁLÓI DEMO: https://www.loom.com/share/2a98a749d13e46a9881ddccd73519d39