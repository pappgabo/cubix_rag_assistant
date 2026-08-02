import { openai, CHAT_MODEL } from "@/lib/openai";
import {
  RAG_GENERATION_TEMPERATURE,
  RAG_MAX_COMPLETION_TOKENS,
  RAG_STRATEGY,
  RAG_TOP_K,
} from "@/lib/ragConfig";
import { loadPrompt, renderTemplate } from "@/lib/prompts";
import { PgvectorVectorStore } from "@/lib/vectorstore/pgvector";
import type { RagQueryResult, RagSource } from "./types";

/** Rollback útvonal: TS retrieval + OpenAI (RAG_BACKEND=inline). */
export async function runInlineRag(params: {
  question: string;
  sessionId: string;
}): Promise<RagQueryResult & { promptTokens: number; completionTokens: number }> {
  const results = await PgvectorVectorStore.search(
    params.question,
    RAG_TOP_K,
    RAG_STRATEGY,
    params.sessionId
  );

  const sources: RagSource[] = results.map((r) => ({
    docId: r.id,
    baseId: (r.payload?.base_id as string | undefined) ?? r.id,
    text: r.text,
    score: r.score,
  }));

  const contextText = results
    .map((r) => r.text)
    .filter(Boolean)
    .join("\n\n---\n\n");

  const systemPrompt = loadPrompt("rag/system.txt");
  const userTemplate = loadPrompt("rag/user.template.txt");
  const userPrompt = renderTemplate(userTemplate, {
    question: params.question,
    context: contextText || "[Nincs találat a tudásbázisban]",
  });

  const completion = await openai.chat.completions.create({
    model: CHAT_MODEL,
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    temperature: RAG_GENERATION_TEMPERATURE,
    max_completion_tokens: RAG_MAX_COMPLETION_TOKENS,
  });

  const usage = completion.usage;
  const promptTokens = usage?.prompt_tokens ?? 0;
  const completionTokens = usage?.completion_tokens ?? 0;

  return {
    answer:
      completion.choices[0]?.message?.content ??
      "Nem sikerült választ generálni.",
    sources,
    model: CHAT_MODEL,
    promptTokens,
    completionTokens,
  };
}
