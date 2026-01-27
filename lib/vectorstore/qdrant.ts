// Qdrant REST kliens importálása
import { QdrantClient } from "@qdrant/js-client-rest";

// OpenAI kliens embedding generáláshoz
import OpenAI from "openai";

// A Qdrant collection neve, ahová a dokumentumok kerülnek
const QDRANT_COLLECTION = "documents";

// OpenAI kliens inicializálása
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!, // biztosan létezik
});

// Qdrant kliens inicializálása
const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL ?? "http://localhost:6333",
  apiKey: process.env.QDRANT_API_KEY || undefined,
});

// A dokumentumok típusa, amit indexelni fogunk
export type DocInput = {
  id?: string;                     // opcionális ID
  text: string;                    // a dokumentum szövege
  metadata?: Record<string, any>;  // tetszőleges metaadat
};

// A vector store osztály
export class QdrantVectorStore {

  // Biztosítja, hogy a collection létezik Qdrantban
  static async ensureCollection(vectorSize: number) {
    const collections = await qdrant.getCollections();

    // Megnézi, hogy létezik-e a "documents" nevű collection
    const exists = collections.collections?.some(
      (c: any) => c.name === QDRANT_COLLECTION
    );

    // Ha nem létezik, létrehozza a megfelelő vektormérettel
    if (!exists) {
      await qdrant.createCollection(QDRANT_COLLECTION, {
        vectors: {
          size: vectorSize,   // embedding mérete
          distance: "Cosine", // Cosine similarity
        },
      });
    }
  }

  // Embedding generálás OpenAI-val
  static async embedTexts(texts: string[]): Promise<number[][]> {
    const resp = await openai.embeddings.create({
      model: process.env.EMBEDDING_MODEL ?? "text-embedding-3-small",
      input: texts,
      encoding_format: "float",
    });

    // A válaszból csak az embedding tömböket adjuk vissza
    return resp.data.map((item: any) => item.embedding as number[]);
  }

  // Dokumentumok indexelése Qdrantba
  static async indexDocuments(docs: DocInput[]) {
    if (docs.length === 0) return;

    // Szövegek kinyerése
    const texts = docs.map((d) => d.text);

    // Embeddingek generálása
    const embeddings = await this.embedTexts(texts);
    const vectorSize = embeddings[0].length;

    // Collection létrehozása, ha kell
    await this.ensureCollection(vectorSize);

    // Qdrant pontok összeállítása
    const points = docs.map((doc, i) => ({
      id: doc.id ?? `${Date.now()}-${i}`, // automatikus ID
      vector: embeddings[i],              // embedding vektor
      payload: {
        text: doc.text,                   // eredeti szöveg
        ...(doc.metadata ?? {}),          // metaadatok
      },
    }));

    // Feltöltés Qdrantba
    await qdrant.upsert(QDRANT_COLLECTION, { points });
  }

  // Hasonló dokumentumok keresése
  static async search(query: string, limit = 5) {
    // Embedding generálása a keresési lekérdezésből
    const [embedding] = await this.embedTexts([query]);

    // Collection biztosítása
    await this.ensureCollection(embedding.length);

    // Vektoros keresés Qdrantban
    const result = await qdrant.query(QDRANT_COLLECTION, {
      query: embedding,
      limit,
      with_payload: true, // kérjük vissza a szöveget is
    });

    // Találatok visszaadása
    return (
      result?.points?.map((p: any) => ({
        score: p.score,
        text: p.payload?.text as string,
        payload: p.payload,
      })) ?? []
    );
  }
}
