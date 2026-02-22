import OpenAI from "openai";
import crypto from "crypto";
import { pool } from "@/lib/db";

// LLM usage logoló modul (ugyanaz a rendszer, mint Pythonban)
import { logLlmUsage } from "@/lib/monitoring/llmUsageLog";
import { calcCostUsd } from "@/lib/monitoring/llmUsageLog";

// Dokumentum input típusa
export type DocInput = {
  id?: string;
  text: string;
  metadata?: Record<string, any>;
};

// OpenAI kliens
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
});

// -----------------------------------------------------------------------------
// Pgvector alapú vector store
// Feladata: embedding generálás, dokumentumok indexelése, keresés pgvectorral
// -----------------------------------------------------------------------------
export class PgvectorVectorStore {

  // ---------------------------------------------------------------------------
  // 1) Embedding generálás OpenAI-val + egységes LLM logolás
  //
  // - sessionId: a teljes RAG-eval futás azonosítója
  // - requestId: egyetlen embedding API-hívás azonosítója
  //
  // Minden hívás logolva lesz:
  //   - latency
  //   - token usage
  //   - költség
  //   - success / error
  // ---------------------------------------------------------------------------
  static async embedTexts(
    texts: string[],
    sessionId: string
  ): Promise<number[][]> {

    const startedAt = Date.now();
    const model = process.env.EMBEDDING_MODEL ?? "text-embedding-3-small";

    // Egyedi requestId minden embedding híváshoz
    const requestId = `embed-${crypto.randomUUID().slice(0, 8)}`;

    try {
      const resp = await openai.embeddings.create({
        model,
        input: texts,
        encoding_format: "float",
      });

      const latencyMs = Date.now() - startedAt;
      const promptTokens = resp.usage?.total_tokens ?? 0;

      // Sikeres logolás
      await logLlmUsage({
        timestamp: new Date().toISOString(),
        requestId,
        sessionId,
        component: "rag-embed",
        model,
        provider: "openai",
        promptTokens,
        completionTokens: 0,
        totalTokens: promptTokens,
        costUsd: calcCostUsd(model, promptTokens, 0),
        latencyMs,
        success: true
        
      });

      return resp.data.map((item: any) => item.embedding as number[]);
    } catch (err: any) {

      // Hiba logolása
      await logLlmUsage({
        timestamp: new Date().toISOString(),
        requestId,
        sessionId,
        component: "rag-embed",
        model,
        provider: "openai",
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0,
        costUsd: 0,
        latencyMs: Date.now() - startedAt,
        success: false,
        errorMessage: err?.message ?? "Unknown error"
      });

      throw err;
    }
  }

  // ---------------------------------------------------------------------------
  // 2) Dokumentumok indexelése PostgreSQL + pgvector táblába
  //
  // - baseline: teljes dokumentumok
  // - chunked: szeletelt dokumentumok
  //
  // Embedding generálás → beszúrás → tranzakció
  // ---------------------------------------------------------------------------
  static async indexDocuments(
    docs: DocInput[],
    table: "baseline" | "chunked" = "baseline",
    sessionId: string
  ) {
    if (docs.length === 0) return;

    const tableName =
      table === "baseline" ? "documents_baseline" : "documents_chunks";

    const texts = docs.map((d) => d.text);

    // Embedding generálás sessionId-vel
    const embeddings = await this.embedTexts(texts, sessionId);

    const client = await pool.connect();
    try {
      await client.query("BEGIN");

      for (let i = 0; i < docs.length; i++) {
        const doc = docs[i];
        const embedding = embeddings[i];

        const docId = doc.id ?? `${Date.now()}-${i}`;
        const embeddingLiteral = `[${embedding.join(",")}]`;

        await client.query(
          `
          INSERT INTO ${tableName} (doc_id, text, embedding, metadata)
          VALUES ($1, $2, $3::vector, $4)
          `,
          [
            docId,
            doc.text,
            embeddingLiteral,
            doc.metadata ?? {}
          ]
        );
      }

      await client.query("COMMIT");
    } catch (err) {
      await client.query("ROLLBACK");
      throw err;
    } finally {
      client.release();
    }
  }

  // ---------------------------------------------------------------------------
  // 3) Hasonló dokumentumok keresése pgvector segítségével
  //
  // - cosine similarity
  // - sessionId továbbadása az embedding híváshoz
  // ---------------------------------------------------------------------------
  static async search(
    query: string,
    limit = 5,
    table: "baseline" | "chunked" = "baseline",
    sessionId: string
  ) {
    const tableName =
      table === "baseline" ? "documents_baseline" : "documents_chunks";

    // A keresési lekérdezés embeddingje
    const [embedding] = await this.embedTexts([query], sessionId);

    const embeddingLiteral = `[${embedding.join(",")}]`;

    const res = await pool.query(
      `
      SELECT doc_id, text, metadata,
             1 - (embedding <=> $1::vector) AS score
      FROM ${tableName}
      ORDER BY embedding <=> $1::vector
      LIMIT $2
      `,
      [embeddingLiteral, limit]
    );

    return res.rows.map((row) => ({
      id: row.doc_id as string,
      score: Number(row.score),
      text: row.text as string,
      payload: row.metadata as Record<string, any>,
    }));
  }
}
