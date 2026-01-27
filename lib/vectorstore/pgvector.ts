// OpenAI kliens importálása az embedding generáláshoz
import OpenAI from "openai";

// A PostgreSQL connection pool, amit korábban hoztál létre
import { pool } from "@/lib/db";

// A dokumentum input típusa, amit az API endpoint is használ
export type DocInput = {
  id?: string;                       // Opcionális egyedi azonosító
  text: string;                      // A dokumentum szövege
  metadata?: Record<string, any>;    // Tetszőleges metaadatok
};

// OpenAI kliens inicializálása
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!, // API kulcs környezeti változóból
});

// A pgvector alapú vector store osztály
export class PgvectorVectorStore {

  // ------------------------------------------------------------
  // 1) Embedding generálás OpenAI-val
  // ------------------------------------------------------------
  static async embedTexts(texts: string[]): Promise<number[][]> {
    // Tömbben küldjük be a szövegeket → OpenAI egyszerre embedeli őket
    const resp = await openai.embeddings.create({
      model: process.env.EMBEDDING_MODEL ?? "text-embedding-3-small",
      input: texts,
      encoding_format: "float", // float32 tömbként kérjük vissza
    });

    // A válaszból csak a vektorokat vesszük ki
    return resp.data.map((item: any) => item.embedding as number[]);
  }

  // ------------------------------------------------------------
  // 2) Dokumentumok indexelése PostgreSQL + pgvector táblába
  // ------------------------------------------------------------
  static async indexDocuments(docs: DocInput[]) {
    if (docs.length === 0) return; // nincs mit indexelni

    // A dokumentumok szövegeit kivesszük
    const texts = docs.map((d) => d.text);

    // Embedding generálás minden dokumentumhoz
    const embeddings = await this.embedTexts(texts);

    // PostgreSQL tranzakció indítása
    const client = await pool.connect();
    try {
      await client.query("BEGIN");

      // Minden dokumentumot beszúrunk a táblába
      for (let i = 0; i < docs.length; i++) {
        const doc = docs[i];
        const embedding = embeddings[i];

        // Ha nincs id, generálunk egyet timestamp alapján
        const docId = doc.id ?? `${Date.now()}-${i}`;
        
        // number[] -> "[v1,v2, ...]" string
        const embeddingLiteral = `[${embedding.join(",")}]`;

        // Beszúrás a documents táblába
        await client.query(
          `
          INSERT INTO documents (doc_id, text, embedding, metadata)
          VALUES ($1, $2, $3::vector, $4)
          `,
          [
            docId,                 // dokumentum azonosító
            doc.text,              // eredeti szöveg
            embeddingLiteral,      // embedding vektor 
            doc.metadata ?? {},    // metaadatok JSON-ként
          ]
        );
      }

      // Tranzakció lezárása
      await client.query("COMMIT");
    } catch (err) {
      // Hiba esetén visszagörgetjük a tranzakciót
      await client.query("ROLLBACK");
      throw err;
    } finally {
      // Kapcsolat visszaadása a poolnak
      client.release();
    }
  }

  // ------------------------------------------------------------
  // 3) Hasonló dokumentumok keresése pgvector segítségével
  // ------------------------------------------------------------
  static async search(query: string, limit = 5) {
    // A keresési lekérdezés embeddingje
    const [embedding] = await this.embedTexts([query]);

    // number[] -> "[v1,v2, ...]" string
    const embeddingLiteral = `[${embedding.join(",")}]`;

    // SQL similarity search pgvectorral
    const res = await pool.query(
      `
      SELECT text, metadata,
             1 - (embedding <=> $1::vector) AS score  -- cosine similarity pontszám
      FROM documents
      ORDER BY embedding <=> $1::vector              -- legkisebb távolság = legjobb találat
      LIMIT $2
      `,
      [embeddingLiteral, limit]
    );

    // A találatok visszaalakítása JS objektummá
    return res.rows.map((row) => ({
      score: Number(row.score),              // 0–1 közötti hasonlósági érték
      text: row.text as string,              // a dokumentum szövege
      payload: row.metadata as Record<string, any>, // metaadatok
    }));
  }
}
