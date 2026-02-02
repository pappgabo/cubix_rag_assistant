// OpenAI kliens importálása az embedding generáláshoz
import OpenAI from "openai";

// PostgreSQL connection pool (korábban létrehozva)
import { pool } from "@/lib/db";

// A dokumentum input típusa, amit az API endpoint is használ
export type DocInput = {
  id?: string;                    // Opcionális egyedi azonosító (ha nincs, generáljuk)
  text: string;                   // A dokumentum szövege
  metadata?: Record<string, any>; // Tetszőleges metaadatok (JSON)
};

// OpenAI kliens inicializálása
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!, // API kulcs környezeti változóból
});

// -----------------------------------------------------------------------------
// Pgvector alapú vector store osztály
// Feladata: embedding generálás, dokumentumok indexelése, keresés pgvectorral
// -----------------------------------------------------------------------------
export class PgvectorVectorStore {

  // ---------------------------------------------------------------------------
  // 1) Embedding generálás OpenAI-val
  // Több szöveget egyszerre küldünk be → gyorsabb és olcsóbb
  // ---------------------------------------------------------------------------
  static async embedTexts(texts: string[]): Promise<number[][]> {
    const resp = await openai.embeddings.create({
      model: process.env.EMBEDDING_MODEL ?? "text-embedding-3-small",
      input: texts,
      encoding_format: "float", // float32-es tömbként kérjük vissza
    });

    // Csak a vektorokat adjuk vissza
    return resp.data.map((item: any) => item.embedding as number[]);
  }

  // ---------------------------------------------------------------------------
  // 2) Dokumentumok indexelése PostgreSQL + pgvector táblába
  //
  // ÚJ: a `table` paraméterrel megadható, hogy melyik táblába írjunk:
  //   - "baseline" → documents_baseline
  //   - "chunked"  → documents_chunks
  //
  // Ez lehetővé teszi, hogy két különböző RAG-stratégiát tároljunk és teszteljünk.
  // ---------------------------------------------------------------------------
  static async indexDocuments(
    docs: DocInput[],
    table: "baseline" | "chunked" = "baseline"
  ) {
    if (docs.length === 0) return;

    // A megfelelő tábla kiválasztása
    const tableName =
      table === "baseline" ? "documents_baseline" : "documents_chunks";

    // A dokumentumok szövegei
    const texts = docs.map((d) => d.text);

    // Embedding generálás
    const embeddings = await this.embedTexts(texts);

    // PostgreSQL tranzakció indítása
    const client = await pool.connect();
    try {
      await client.query("BEGIN");

      // Minden dokumentum beszúrása
      for (let i = 0; i < docs.length; i++) {
        const doc = docs[i];
        const embedding = embeddings[i];

        // Ha nincs ID, generálunk egyet
        const docId = doc.id ?? `${Date.now()}-${i}`;

        // number[] → "[1,2,3,...]" formátum
        const embeddingLiteral = `[${embedding.join(",")}]`;

        // Dinamikus tábla neve → SQL injection veszély nincs, mert enum alapján választjuk
        await client.query(
          `
          INSERT INTO ${tableName} (doc_id, text, embedding, metadata)
          VALUES ($1, $2, $3::vector, $4)
          `,
          [
            docId,            // dokumentum azonosító
            doc.text,         // eredeti szöveg
            embeddingLiteral, // embedding vektor
            doc.metadata ?? {} // metaadatok JSON-ként
          ]
        );
      }

      await client.query("COMMIT");
    } catch (err) {
      // Hiba esetén rollback
      await client.query("ROLLBACK");
      throw err;
    } finally {
      client.release();
    }
  }

  // ---------------------------------------------------------------------------
  // 3) Hasonló dokumentumok keresése pgvector segítségével
  //
  // ÚJ: a `table` paraméterrel megadható, hogy melyik táblából keressünk:
  //   - "baseline" → documents_baseline
  //   - "chunked"  → documents_chunked
  //
  // A keresés cosine similarity alapján történik.
  // ---------------------------------------------------------------------------
  static async search(
    query: string,
    limit = 5,
    table: "baseline" | "chunked" = "baseline"
  ) {
    // A megfelelő tábla kiválasztása
    const tableName =
      table === "baseline" ? "documents_baseline" : "documents_chunks";

    // A keresési lekérdezés embeddingje
    const [embedding] = await this.embedTexts([query]);

    // number[] → "[1,2,3,...]"
    const embeddingLiteral = `[${embedding.join(",")}]`;

    // SQL similarity search pgvectorral
    const res = await pool.query(
      `
      SELECT doc_id, text, metadata,
             1 - (embedding <=> $1::vector) AS score  -- cosine similarity
      FROM ${tableName}
      ORDER BY embedding <=> $1::vector              -- legkisebb távolság = legjobb találat
      LIMIT $2
      `,
      [embeddingLiteral, limit]
    );

    // A találatok visszaalakítása JS objektummá
    return res.rows.map((row) => ({
      id: row.doc_id as string,
      score: Number(row.score),
      text: row.text as string,
      payload: row.metadata as Record<string, any>,
    }));
  }
}
