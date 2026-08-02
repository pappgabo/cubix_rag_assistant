import {
  RAG_RETRIEVAL_STRATEGY,
  RAG_SERVICE_URL,
  RAG_TOP_K,
} from "@/lib/ragConfig";
import type { RagQueryResult, RagSource } from "./types";

interface RagServiceChunk {
  doc_id: string;
  base_id: string;
  text: string;
  score: number;
}

interface RagServiceResponse {
  answer: string;
  chunks?: RagServiceChunk[];
  model?: string;
}

function mapChunks(chunks: RagServiceChunk[] | undefined): RagSource[] {
  return (chunks ?? []).map((c) => ({
    docId: c.doc_id,
    baseId: c.base_id,
    text: c.text,
    score: c.score,
  }));
}

export async function queryRagService(params: {
  question: string;
  sessionId: string;
  requestId: string;
}): Promise<RagQueryResult> {
  const url = `${RAG_SERVICE_URL}/v1/rag/query`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: params.question,
      session_id: params.sessionId,
      request_id: params.requestId,
      top_k: RAG_TOP_K,
      strategy: RAG_RETRIEVAL_STRATEGY,
      prompt_version: "prod",
    }),
  });

  if (!resp.ok) {
    let detail = `RAG service HTTP ${resp.status}`;
    try {
      const errBody = await resp.json();
      if (errBody?.detail) {
        detail =
          typeof errBody.detail === "string"
            ? errBody.detail
            : JSON.stringify(errBody.detail);
      }
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }

  const data = (await resp.json()) as RagServiceResponse;
  return {
    answer: data.answer ?? "Nem sikerült választ generálni.",
    sources: mapChunks(data.chunks),
    model: data.model ?? "unknown",
  };
}
