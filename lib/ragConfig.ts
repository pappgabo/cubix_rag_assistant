/** Közös RAG runtime beállítások — ugyanazok az env-kulcsok, mint a Python config.py-ban. */

export type PgvectorTableStrategy = "baseline" | "chunked";

export type RagRetrievalStrategy = "baseline" | "chunked" | "chunked_rerank";

const VALID_PGVECTOR_STRATEGIES = new Set<PgvectorTableStrategy>([
  "baseline",
  "chunked",
]);

const VALID_RAG_STRATEGIES = new Set<RagRetrievalStrategy>([
  "baseline",
  "chunked",
  "chunked_rerank",
]);

function parseRagRetrievalStrategy(
  raw: string | undefined
): RagRetrievalStrategy {
  const value = (raw ?? "baseline").toLowerCase();
  if (VALID_RAG_STRATEGIES.has(value as RagRetrievalStrategy)) {
    return value as RagRetrievalStrategy;
  }
  return "baseline";
}

function parsePgvectorStrategy(raw: string | undefined): PgvectorTableStrategy {
  const value = (raw ?? "baseline").toLowerCase();
  // A TS retrieval csak baseline/chunked táblát ismer; rerank a Python oldalon van.
  if (value === "chunked" || value === "chunked_rerank") {
    return "chunked";
  }
  if (VALID_PGVECTOR_STRATEGIES.has(value as PgvectorTableStrategy)) {
    return value as PgvectorTableStrategy;
  }
  return "baseline";
}

export const RAG_GENERATION_TEMPERATURE = Number(
  process.env.RAG_GENERATION_TEMPERATURE ?? "0.7"
);

export const RAG_MAX_COMPLETION_TOKENS = Number(
  process.env.RAG_MAX_COMPLETION_TOKENS ?? "400"
);

export const RAG_TOP_K = Number(process.env.RAG_TOP_K ?? "5");

export const RAG_RETRIEVAL_STRATEGY = parseRagRetrievalStrategy(
  process.env.RAG_STRATEGY
);

export const RAG_STRATEGY = parsePgvectorStrategy(process.env.RAG_STRATEGY);

export const RAG_SERVICE_URL = (
  process.env.RAG_SERVICE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

/** service = FastAPI rag_core (default); inline = TS rollback útvonal */
export const RAG_BACKEND =
  process.env.RAG_BACKEND === "inline" ? "inline" : "service";
