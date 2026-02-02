// app/api/upload-docs/route.ts

// Qdrant vector store és a dokumentum input típus importálása
import { QdrantVectorStore, DocInput } from "@/lib/vectorstore/qdrant";
import { PgvectorVectorStore } from "@/lib/vectorstore/pgvector";

export async function POST(req: Request) {
  try {
    // ------------------------------------------------------------
    // 1) STRATÉGIA KINYERÉSE AZ URL-BŐL
    //    /api/upload-docs?strategy=baseline
    //    /api/upload-docs?strategy=chunked
    // ------------------------------------------------------------
    const { searchParams } = new URL(req.url);
    const strategy = searchParams.get("strategy") as "baseline" | "chunked";

    // Ha a Python ingest nem küldte → legyen baseline
    const finalStrategy = strategy || "baseline";

    // ------------------------------------------------------------
    // 2) Request body beolvasása
    // ------------------------------------------------------------
    const body = await req.json().catch(() => null);

    if (!Array.isArray(body)) {
      return Response.json(
        { error: "A request body egy tömb legyen (Array) dokumentum objektumokkal." },
        { status: 400 }
      );
    }

    // ------------------------------------------------------------
    // 3) Dokumentumok szűrése és normalizálása
    // ------------------------------------------------------------
    const docs: DocInput[] = body
      .filter(
        (item) =>
          item &&
          typeof item === "object" &&
          typeof item.text === "string" &&
          item.text.trim().length > 0
      )
      .map((item, idx) => ({
        id: item.id ?? `${Date.now()}-${idx}`,
        text: item.text,
        metadata: item.metadata ?? {},
      }));

    if (docs.length === 0) {
      return Response.json(
        { error: "Nem érkezett érvényes dokumentum (hiányzó vagy üres 'text' mező)." },
        { status: 400 }
      );
    }

    console.log(`>>> Ingest indítása: Stratégia = ${finalStrategy}`);
    console.log(`>>> Dokumentumok száma: ${docs.length}`);

    // ------------------------------------------------------------
    // 4) Indexelés a megfelelő pipeline-ba
    // ------------------------------------------------------------
    await PgvectorVectorStore.indexDocuments(docs, finalStrategy);

    // ------------------------------------------------------------
    // 5) Sikeres válasz
    // ------------------------------------------------------------
    return Response.json(
      {
        ok: true,
        appliedStrategy: finalStrategy,
        receivedCount: body.length,
        validCount: docs.length,
      },
      { status: 200 }
    );

  } catch (err) {
    console.error(err);
    return Response.json(
      { error: "Váratlan hiba történt az upload-docs endpointban." },
      { status: 500 }
    );
  }
}
