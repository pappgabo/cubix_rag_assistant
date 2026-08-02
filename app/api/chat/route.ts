import { CHAT_MODEL } from "@/lib/openai";
import { RAG_BACKEND } from "@/lib/ragConfig";
import { calcCostUsd, logLlmUsage } from "@/lib/monitoring/llmUsageLog";
import { applySafetyFilter } from "@/lib/chat/safetyFilter";
import { runInlineRag } from "@/lib/chat/inlineRag";
import { queryRagService } from "@/lib/chat/ragServiceClient";
import crypto from "crypto";

export async function POST(req: Request) {
  const requestId = crypto.randomUUID();
  const startedAt = Date.now();

  try {
    const body = await req.json().catch(() => null);
    const question = body?.question as string | undefined;
    const incomingSessionId = body?.sessionId as string | undefined;

    let sessionId: string;
    let componentName: string;

    if (incomingSessionId) {
      sessionId = incomingSessionId;
      componentName = "eval-chat";
    } else {
      sessionId = `prod-${requestId}`;
      componentName = "chat";
    }

    if (!question || !question.trim()) {
      return Response.json(
        { error: "A 'question' mező kötelező." },
        { status: 400 }
      );
    }

    let answer: string;
    let sources: Awaited<ReturnType<typeof queryRagService>>["sources"];
    let model: string;
    let promptTokens = 0;
    let completionTokens = 0;

    if (RAG_BACKEND === "inline") {
      const inlineResult = await runInlineRag({ question, sessionId });
      answer = inlineResult.answer;
      sources = inlineResult.sources;
      model = inlineResult.model;
      promptTokens = inlineResult.promptTokens;
      completionTokens = inlineResult.completionTokens;
    } else {
      const serviceResult = await queryRagService({
        question,
        sessionId,
        requestId,
      });
      answer = serviceResult.answer;
      sources = serviceResult.sources;
      model = serviceResult.model;
    }

    answer = applySafetyFilter(answer);

    const latencyMs = Date.now() - startedAt;
    const proxyComponent =
      RAG_BACKEND === "inline"
        ? componentName
        : `${componentName}-proxy`;

    await logLlmUsage({
      timestamp: new Date(startedAt).toISOString(),
      requestId,
      sessionId,
      component: proxyComponent,
      model,
      provider: "openai",
      promptTokens,
      completionTokens,
      totalTokens: promptTokens + completionTokens,
      costUsd:
        RAG_BACKEND === "inline"
          ? calcCostUsd(model, promptTokens, completionTokens)
          : 0,
      latencyMs,
      success: true,
    });

    return Response.json({ ok: true, answer, sources }, { status: 200 });
  } catch (err: unknown) {
    const latencyMs = Date.now() - startedAt;
    const message = err instanceof Error ? err.message : "Unknown error";

    await logLlmUsage({
      timestamp: new Date(startedAt).toISOString(),
      requestId,
      sessionId: `prod-${requestId}`,
      component: RAG_BACKEND === "inline" ? "chat" : "chat-proxy",
      model: CHAT_MODEL,
      provider: "openai",
      promptTokens: 0,
      completionTokens: 0,
      totalTokens: 0,
      costUsd: 0,
      latencyMs,
      success: false,
      errorMessage: message,
    });

    console.error(err);

    const status = RAG_BACKEND === "service" ? 502 : 500;
    const errorMessage =
      RAG_BACKEND === "service"
        ? "A RAG service nem elérhető vagy hibát adott vissza."
        : "Váratlan hiba történt a chat endpointban.";

    return Response.json({ error: errorMessage }, { status });
  }
}
