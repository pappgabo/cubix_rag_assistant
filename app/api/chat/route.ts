// app/api/chat/route.ts
import { QdrantVectorStore } from "@/lib/vectorstore/qdrant";
import { PgvectorVectorStore } from "@/lib/vectorstore/pgvector";
import { openai, CHAT_MODEL } from "@/lib/openai";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => null);
    const question = body?.question as string | undefined;

    if (!question || !question.trim()) {
      return Response.json(
        { error: "A 'question' mező kötelező." },
        { status: 400 }
      );
    }

    // 1) Releváns kontextus Pgvectorból
    const results = await PgvectorVectorStore.search(question, 5);
    const contextText = results
      .map((r) => r.text)
      .filter((t) => !!t)
      .join("\n\n---\n\n");

// 2) Prompt összerakása 0. verzió
    //const systemPrompt =
    //  "Te egy főzőasszisztens vagy, aki kizárólag a megadott kontextus alapján válaszol." +
    //  " Ha a kontextusban nincs elég információ, mondd, hogy nem tudod." +
    //  " Válaszolj magyarul, tömören.";

   //1. verzió
   //const systemPrompt =
   //   "Te egy főzőasszisztens vagy. Kizárólag a felhasználó által megadott kontextus alapján válaszolsz." +
   //   "Nem használsz külső tudást, nem találsz ki információt, és nem egészíted ki a hiányzó részeket." +
   //   "Ha a kontextus nem tartalmaz elegendő adatot a válaszhoz, mondd azt: 'A megadott kontextus alapján ezt nem tudom.’ " +
   //   "Ha édességet vagy desszertet kérnek, jelezd a válaszodban, hogy"
   //   "Mindig magyarul és tömören válaszolj, legfeljebb néhány mondatban." +
   //   "Csak főzéssel, alapanyagokkal, technikákkal vagy receptekkel kapcsolatos kérdésekre reagálsz." +
   //   "A kontextusban szereplő ‘rag’ soha nem tartalmaz édességet vagy desszertet, ezt adottnak tekinted, és nem feltételezel ilyeneket.";
    
   //2. verzió
   // const systemPrompt = 
   //   "Te egy főzőasszisztens vagy. Kizárólag a felhasználó által megadott kontextus alapján válaszolsz. " + 
   //   "Nem használsz külső tudást, nem találsz ki információt, és nem egészíted ki a hiányzó részeket. " + 
   //   "Ha a kontextus nem tartalmaz elegendő adatot a válaszhoz, mondd azt: 'A megadott kontextus alapján ezt nem tudom.' " + 
   //   "Ha édességet vagy desszertet kérnek, jelezd, hogy a rendelkezésre álló kontextusban nincs desszert, " + 
   //   "és inkább ajánlj alternatív főételt vagy egyszerű édes ötletet (pl. gyümölcsalapú megoldás). " + 
   //   "Mindig magyarul és tömören válaszolj, legfeljebb néhány mondatban. " + 
   //   "Csak főzéssel, alapanyagokkal, technikákkal vagy receptekkel kapcsolatos kérdésekre reagálsz. "  + 
   //   "A kontextusban szereplő rag soha nem tartalmaz édességet vagy desszertet, ezt adottnak tekinted, és nem feltételezel ilyeneket.";  


    // 2) System prompt
    const systemPrompt =
      "Te egy főzőasszisztens vagy. Kizárólag a felhasználó által megadott kontextus alapján válaszolsz. " +
      "Nem használsz külső tudást, nem találsz ki információt, és nem egészíted ki a hiányzó részeket. " +
      "Mindig tartsd be a felhasználó által megadott korlátokat: időkeret, alapanyagok, eszközök (pl. sütő/nem sütő), diétás megkötések. " +
      "Ha bármely korlátot nem tudsz teljesen betartani, mondd ki egyértelműen, miben térsz el (pl. 'kb. 60 perc, nem 30'). " +

      "Ha a kontextus nem tartalmaz elegendő adatot a válaszhoz, mondd azt: 'A megadott kontextus alapján ezt nem tudom.' " +

      "Ha a kontextusban nincs pontos találat a kérésre, jelezd röviden: 'Ilyen recept nincs a megadott kontextusban, de tudok ajánlani…', " +
      "és ajánlj olyan alternatívát, amely típusban illeszkedik (pl. leves helyett leves‑jellegű, desszert helyett édes jellegű). " +
      "Alternatíva ajánlásánál is törekedj arra, hogy a felhasználó idő‑, alapanyag‑ és diétás korlátaihoz a lehető legjobban igazodj. " +
      "Ha nem tudsz típusban illeszkedni, magyarázd el világosan, miért nem. " +

      "Vedd figyelembe a felhasználó személyiségét, ha a kontextus utal rá: " +
      "türelmetlen kezdő esetén legyen egyszerű, kevés hozzávalós, kevés lépéses megoldás; " +
      "elfoglalt szülő esetén hangsúlyozd az időt és a realitást (pl. 'ez kb. 60 perc, nem 30'). " +

      "Gyors vacsora alatt legfeljebb kb. 30-40 perc aktív elkészítési időt érts. Ne nevezd gyorsnak azokat a recepteket, " + 
      "amelyek 60 perc körüliek vagy több órás / napos pihentetést igényelnek."

      "Ha édességet vagy desszertet kérnek, jelezd, hogy a rendelkezésre álló kontextusban nincs desszert, " +
      "és ajánlj egyszerű, édes jellegű alternatívát (pl. gyümölcsalapú megoldás), és mondd el, hogy ez csak részben helyettesíti a desszertet. " +

      "Mindig magyarul és tömören válaszolj, legfeljebb néhány mondatban. " +
      "Csak főzéssel, alapanyagokkal, technikákkal vagy receptekkel kapcsolatos kérdésekre reagálsz. " +
      "A kontextusban szereplő rag soha nem tartalmaz édességet vagy desszertet, ezt adottnak tekinted, és nem feltételezel ilyeneket. " +

      "Ugyanarra a kérésre ne ismételd végtelenségig, hogy nem tudod; ha nem tudsz segíteni, egy alkalommal mondd el világosan, majd ne adj új, kitalált részleteket.";

    const userPrompt = `Kérdés: ${question}

Kontextus a dokumentumokból:
${contextText || "[Nincs találat a tudásbázisban]"}`;

    // 3) OpenAI chat hívás
    const completion = await openai.chat.completions.create({
      model: CHAT_MODEL,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.7,   //A temperature ebben a hívásban a modell válaszainak kreativitását 
      // és véletlenszerűségét szabályozza. 0.0 → teljesen determinisztikus ... 0.7–1.0 → kreatív, változatos

    });

    // FONTOS: let, mert felülírhatjuk a guardrail miatt
    let answer =
      completion.choices[0]?.message?.content ??
      "Nem sikerült választ generálni.";

    // 4) Hard-coded biztonsági szűrő
    const DANGEROUS_TERMS = [
      "öngyilkosság",
      "gyilkosság",
      "méreg",
      "tiszafa",
      "cianid",
      "arzén",
      "gyilkos galóca",
      "THC",
      "kokain"
    ];

    const lowerAnswer = answer.toLowerCase();
    const isDangerous = DANGEROUS_TERMS.some(term =>
      lowerAnswer.includes(term)
    );

    if (isDangerous) {
      console.error("SAFETY TRIGGERED: Dangerous content detected!");
      answer =
        "Sajnálom, de technikai vagy biztonsági okokból erre a kérdésre nem válaszolhatok.";
    }

    // 5) Válasz visszaadása
    return Response.json(
      {
        ok: true,
        answer,
      },
      { status: 200 }
    );

  } catch (err) {
    console.error(err);
    return Response.json(
      { error: "Váratlan hiba történt a chat endpointban." },
      { status: 500 }
    );
  }
}