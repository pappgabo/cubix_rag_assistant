// app/api/upload-docs/route.ts

// Qdrant vector store és a dokumentum input típus importálása
import { QdrantVectorStore, DocInput } from "@/lib/vectorstore/qdrant";
import { PgvectorVectorStore } from "@/lib/vectorstore/pgvector";

export async function POST(req: Request) {
  try {
    // A request body beolvasása JSON-ként.
    // Ha nem sikerül parse-olni, akkor null-t ad vissza.
    const body = await req.json().catch(() => null);

    // Ellenőrzés: a body-nak tömbnek kell lennie.
    if (!Array.isArray(body)) {
      return Response.json(
        { error: "A request body egy tömb legyen (Array) dokumentum objektumokkal." },
        { status: 400 }
      );
    }

    // A bejövő tömbből kiszűrjük az érvényes dokumentumokat:
    // - objektum legyen
    // - legyen 'text' mező
    // - a 'text' ne legyen üres
    const docs: DocInput[] = body
      .filter(
        (item) =>
          item &&
          typeof item === "object" &&
          typeof item.text === "string" &&
          item.text.trim().length > 0
      )
      .map((item, idx) => ({
        // Ha nincs id, generálunk egyet timestamp + index alapján
        id: item.id ?? `${Date.now()}-${idx}`,
        text: item.text,
        // Metadata opcionális, ha nincs, üres objektumot adunk
        metadata: item.metadata ?? {},
      }));

    // Ha egyetlen érvényes dokumentum sincs, hibát dobunk
    if (docs.length === 0) {
      return Response.json(
        { error: "Nem érkezett érvényes dokumentum (hiányzó vagy üres 'text' mező)." },
        { status: 400 }
      );
    }

    // A dokumentumok indexelése Qdrantban OpenAI embeddingekkel
    //await QdrantVectorStore.indexDocuments(docs);

    // A dokumentumok indexelése PostgresDB-be OpenAI embeddingekkel
    await PgvectorVectorStore.indexDocuments(docs);
    // Sikeres válasz: mennyi dokumentum érkezett és mennyi volt érvényes
    return Response.json(
      {
        ok: true,
        receivedCount: body.length,
        validCount: docs.length,
      },
      { status: 200 }
    );
  } catch (err) {
    // Ha bármi váratlan hiba történik, logoljuk és 500-at adunk vissza
    console.error(err);
    return Response.json(
      { error: "Váratlan hiba történt az upload-docs endpointban." },
      { status: 500 }
    );
  }
}
