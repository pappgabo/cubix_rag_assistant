import { PgvectorVectorStore } from "@/lib/vectorstore/pgvector";
import { openai, CHAT_MODEL } from "@/lib/openai";
import { calcCostUsd, logLlmUsage } from "@/lib/monitoring/llmUsageLog";
import { loadPrompt, renderTemplate } from "@/lib/prompts";
import crypto from "crypto";

export async function POST(req: Request) {
  // Egyedi azonosító minden kéréshez
  const requestId = crypto.randomUUID();
  const startedAt = Date.now();

  try {
    // 1) Body beolvasása
    const body = await req.json().catch(() => null);
    const question = body?.question as string | undefined;

    // 2) Eredeti sessionId kinyerése (eval futás esetén)
    const incomingSessionId = body?.sessionId as string | undefined;

    // 3) DRÓTOZÁS:
    //    - Ha van incomingSessionId → eval futás
    //    - Ha nincs → prod hívás → kapjon prod- prefixet
    let sessionId: string;
    let componentName: string;

    if (incomingSessionId) {
      sessionId = incomingSessionId;
      componentName = "eval-chat";
    } else {
      sessionId = `prod-${requestId}`;
      componentName = "chat";
    }

    // Validáció
    if (!question || !question.trim()) {
      return Response.json(
        { error: "A 'question' mező kötelező." },
        { status: 400 }
      );
    }

    // -----------------------------------------------------------------------
    // 1) Kontextus lekérése Pgvectorból
    // -----------------------------------------------------------------------
    const results = await PgvectorVectorStore.search(
      question,
      5,
      "baseline",
      sessionId // mindig a közös sessionId-t adjuk át
    );

    const contextText = results
      .map((r) => r.text)
      .filter(Boolean)
      .join("\n\n---\n\n");

    // -----------------------------------------------------------------------
    // 2) Promptok (prompts/rag/)
    // -----------------------------------------------------------------------
    const systemPrompt = loadPrompt("rag/system.txt");
    const userTemplate = loadPrompt("rag/user.template.txt");
    const userPrompt = renderTemplate(userTemplate, {
      question,
      context: contextText || "[Nincs találat a tudásbázisban]",
    });

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

    const latencyMs = Date.now() - startedAt;

    const usage = completion.usage;
    const promptTokens = usage?.prompt_tokens ?? 0;
    const completionTokens = usage?.completion_tokens ?? 0;
    const totalTokens = usage?.total_tokens ?? promptTokens + completionTokens;

    const costUsd = calcCostUsd(CHAT_MODEL, promptTokens, completionTokens);

    let answer =
      completion.choices[0]?.message?.content ??
      "Nem sikerült választ generálni.";

    // -----------------------------------------------------------------------
    // 4) Biztonsági szűrő
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

    if (DANGEROUS_TERMS.some((t) => answer.toLowerCase().includes(t))) {
      console.error("SAFETY TRIGGERED: Dangerous content detected!");
      answer =
        "Sajnálom, de technikai vagy biztonsági okokból erre a kérdésre nem válaszolhatok.";
    }

    // -----------------------------------------------------------------------
    // 5) LLM logolás
    // -----------------------------------------------------------------------
    await logLlmUsage({
      timestamp: new Date(startedAt).toISOString(),
      requestId,
      sessionId,
      component: componentName,
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
    // 6) Válasz visszaadása
    // -----------------------------------------------------------------------
    return Response.json({ ok: true, answer }, { status: 200 });
  } catch (err: any) {
    const latencyMs = Date.now() - startedAt;

    await logLlmUsage({
      timestamp: new Date(startedAt).toISOString(),
      requestId,
      sessionId: `prod-${requestId}`,
      component: "chat",
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
