import { PgvectorVectorStore } from "@/lib/vectorstore/pgvector";
import type { DocInput } from "@/lib/vectorstore/pgvector";

/**
 * A fájlnévből készít egy base_id-t.
 * Példa: "pita-bread.md" → "pita-bread"
 * A base_id a dokumentum logikai azonosítója (chunkolásnál minden chunk ezt örökli).
 */
function makeBaseIdFromFilename(filename: string): string {
  return filename.replace(/\.[^.]+$/, "");
}

export async function POST(req: Request) {
  try {
    // ------------------------------------------------------------
    // 1) STRATÉGIA KINYERÉSE (baseline vagy chunked)
    // ------------------------------------------------------------
    const { searchParams } = new URL(req.url);
    const strategy = searchParams.get("strategy") as "baseline" | "chunked";
    const finalStrategy = strategy || "baseline";

    // ------------------------------------------------------------
    // 2) Request body beolvasása és validálása
    // ------------------------------------------------------------
    const body = await req.json().catch(() => null);

    if (!Array.isArray(body)) {
      return Response.json(
        { error: "A request body egy tömb legyen (Array) dokumentum objektumokkal." },
        { status: 400 },
      );
    }

    // ------------------------------------------------------------
    // 3) Dokumentumok normalizálása
    //
    // Itt történik:
    // - text mező ellenőrzése
    // - bejövő id átvétele (slug vagy slug_index)
    // - filename / id alapján base_id meghatározása
    // - metadata kiegészítése base_id-vel
    // ------------------------------------------------------------
    const docs: DocInput[] = body
      .filter(
        (item) =>
          item &&
          typeof item === "object" &&
          typeof item.text === "string" &&
          item.text.trim().length > 0,
      )
      .map((item, idx) => {
        const metadata = item.metadata ?? {};
        const filename: string | undefined = metadata.filename;

        // 1) Ha jön id a kliensből (Python) → azt használjuk
        //    baseline: "bagels"
        //    chunked:  "bagels_0"
        const incomingId: string | undefined = item.id;

        // 2) base_id:
        //    - ha metadata.base_id létezik → azt használjuk
        //    - ha nincs, de van filename → abból képezzük
        //    - ha nincs filename, de az incomingId tartalmaz "_" → első rész
        //    - különben fallback: incomingId vagy "doc_0", "doc_1", ...
        let baseId: string | undefined = metadata.base_id;

        if (!baseId) {
          if (typeof filename === "string") {
            baseId = makeBaseIdFromFilename(filename);
          } else if (typeof incomingId === "string" && incomingId.includes("_")) {
            baseId = incomingId.split("_")[0];
          } else if (typeof incomingId === "string") {
            baseId = incomingId;
          } else {
            baseId = `doc_${idx}`;
          }
        }

        return {
          // A doc_id mostantól = bejövő id (slug / slug_index), vagy fallback ha nincs
          id: incomingId ?? baseId ?? `doc_${idx}`,
          text: item.text,
          metadata: {
            ...metadata,
            base_id: baseId,
          },
        };
      });

    if (docs.length === 0) {
      return Response.json(
        { error: "Nem érkezett érvényes dokumentum (hiányzó vagy üres 'text' mező)." },
        { status: 400 },
      );
    }

    console.log(`>>> Ingest indítása: Stratégia = ${finalStrategy}`);
    console.log(`>>> Dokumentumok száma: ${docs.length}`);

    // ------------------------------------------------------------
    // 4) Dokumentumok indexelése pgvector-ba
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
      { status: 200 },
    );
  } catch (err) {
    console.error(err);
    return Response.json(
      { error: "Váratlan hiba történt az upload-docs endpointban." },
      { status: 500 },
    );
  }
}