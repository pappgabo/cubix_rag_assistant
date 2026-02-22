import { PgvectorVectorStore } from "@/lib/vectorstore/pgvector";
import { openai, CHAT_MODEL } from "@/lib/openai";
import { calcCostUsd, logLlmUsage } from "@/lib/monitoring/llmUsageLog";
import crypto from "crypto";

export async function POST(req: Request) {
  // Egyedi azonosító minden bejövő kéréshez (LLM logoláshoz is kell)
  const requestId = crypto.randomUUID();

  // A teljes hívás latency-jének mérése
  const startedAt = Date.now();

  try {
    // A kérés JSON testének beolvasása
    const body = await req.json().catch(() => null);
    const question = body?.question as string | undefined;

    // Ha eval futásból jön → sessionId jelen lesz
    const sessionId = body?.sessionId as string | undefined;

    // 🔥 ÚJ: komponens meghatározása
    // Ha van sessionId → ez egy eval futás része
    // Ha nincs → normál chat hívás
    const componentName = sessionId ? "eval-chat" : "chat";

    // Validáció
    if (!question || !question.trim()) {
      return Response.json(
        { error: "A 'question' mező kötelező." },
        { status: 400 }
      );
    }

    // -----------------------------------------------------------------------
    // 1) Kontextus lekérése Pgvectorból
    //    A search() már sessionId-t vár → ha nincs eval, requestId-t adunk
    // -----------------------------------------------------------------------
    const results = await PgvectorVectorStore.search(
      question,
      5,
      "baseline",
      sessionId ?? requestId
    );

    // A találatok szövegének összefűzése
    const contextText = results
      .map((r) => r.text)
      .filter(Boolean)
      .join("\n\n---\n\n");

    // -----------------------------------------------------------------------
    // 2) System prompt — a főzőasszisztens működési szabályai
    // -----------------------------------------------------------------------
    const systemPrompt =
      "Te egy főzőasszisztens vagy. Kizárólag a felhasználó által megadott kontextus alapján válaszolsz. " +
      "Nem használsz külső tudást, nem találsz ki információt, és nem egészíted ki a hiányzó részeket. " +
      "Mindig tartsd be a felhasználó által megadott korlátokat: időkeret, alapanyagok, eszközök, diétás megkötések. " +
      "Ha a kontextus nem tartalmaz elegendő adatot, mondd azt: 'A megadott kontextus alapján ezt nem tudom.' " +
      "Mindig magyarul és tömören válaszolj.";

    // Felhasználói prompt
    const userPrompt = `Kérdés: ${question}

Kontextus a dokumentumokból:
${contextText || "[Nincs találat a tudásbázisban]"}`;

    // -----------------------------------------------------------------------
    // 3) OpenAI chat hívás
    // -----------------------------------------------------------------------
    const completion = await openai.chat.completions.create({
      model: CHAT_MODEL,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.7,
    });

    // Latency mérése
    const latencyMs = Date.now() - startedAt;

    // Tokenhasználat
    const usage = completion.usage;
    const promptTokens = usage?.prompt_tokens ?? 0;
    const completionTokens = usage?.completion_tokens ?? 0;
    const totalTokens = usage?.total_tokens ?? promptTokens + completionTokens;

    // Költség számítása
    const costUsd = calcCostUsd(CHAT_MODEL, promptTokens, completionTokens);

    // Modell válasza
    let answer =
      completion.choices[0]?.message?.content ??
      "Nem sikerült választ generálni.";

    // -----------------------------------------------------------------------
    // 4) Biztonsági szűrő — veszélyes tartalmak kiszűrése
    // -----------------------------------------------------------------------
    const DANGEROUS_TERMS = [
      "öngyilkosság",
      "gyilkosság",
      "méreg",
      "tiszafa",
      "cianid",
      "arzén",
      "gyilkos galóca",
      "THC",
      "kokain",
    ];

    const lowerAnswer = answer.toLowerCase();
    const isDangerous = DANGEROUS_TERMS.some((term) =>
      lowerAnswer.includes(term)
    );

    if (isDangerous) {
      console.error("SAFETY TRIGGERED: Dangerous content detected!");
      answer =
        "Sajnálom, de technikai vagy biztonsági okokból erre a kérdésre nem válaszolhatok.";
    }

    // -----------------------------------------------------------------------
    // 5) LLM-használat naplózása
    //    🔥 Itt használjuk az új componentName mezőt
    // -----------------------------------------------------------------------
    await logLlmUsage({
      timestamp: new Date(startedAt).toISOString(),
      requestId,
      sessionId: sessionId ?? null,
      component: componentName, // <-- EZ A LÉNYEG
      model: CHAT_MODEL,
      provider: "openai",
      promptTokens,
      completionTokens,
      totalTokens,
      costUsd,
      latencyMs,
      success: true,
    });

    // -----------------------------------------------------------------------
    // 6) Válasz visszaküldése
    // -----------------------------------------------------------------------
    return Response.json(
      {
        ok: true,
        answer,
      },
      { status: 200 }
    );
  } catch (err: any) {
    const latencyMs = Date.now() - startedAt;

    // -----------------------------------------------------------------------
    // Hiba esetén is logolunk
    // -----------------------------------------------------------------------
    await logLlmUsage({
      timestamp: new Date(startedAt).toISOString(),
      requestId,
      sessionId: null,
      component: "chat", // hibánál nincs eval → marad chat
      model: CHAT_MODEL,
      provider: "openai",
      promptTokens: 0,
      completionTokens: 0,
      totalTokens: 0,
      costUsd: 0,
      latencyMs,
      success: false,
      errorMessage: err?.message ?? "Unknown error",
    });

    console.error(err);

    return Response.json(
      { error: "Váratlan hiba történt a chat endpointban." },
      { status: 500 }
    );
  }
}
