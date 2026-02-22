// lib/llmUsageLog.ts

import fs from "fs";
import path from "path";

// -----------------------------------------------------------------------------
// LLM usage log entry type
// -----------------------------------------------------------------------------
export type LlmUsageLogEntry = {
  timestamp: string;
  requestId: string;
  sessionId?: string | null;

  component: string;
  model: string;
  provider: string;

  promptTokens: number;
  completionTokens: number;
  totalTokens: number;

  costUsd: number;
  latencyMs: number;

  success: boolean;
  errorMessage?: string | null;
};

// -----------------------------------------------------------------------------
// Model pricing table (USD per 1000 tokens)
// -----------------------------------------------------------------------------
const MODEL_PRICES_USD_PER_1K_TOKENS: Record<
  string,
  { input: number; output: number }
> = {
  "gpt-4.1-mini": { input: 0.00015, output: 0.0006 },
  "gpt-4.1": { input: 0.005, output: 0.015 },
  "text-embedding-3-small": { input: 0.00002, output: 0 },
};

// -----------------------------------------------------------------------------
// Cost calculation with 8-decimal precision
// -----------------------------------------------------------------------------
export function calcCostUsd(
  model: string,
  promptTokens: number,
  completionTokens: number
): number {
  const prices = MODEL_PRICES_USD_PER_1K_TOKENS[model];
  if (!prices) return 0;

  const inputCost = (promptTokens / 1000) * prices.input;
  const outputCost = (completionTokens / 1000) * prices.output;

  // 8 tizedesjegy → embedding költségek is látszanak
  return Number((inputCost + outputCost).toFixed(8));
}

// -----------------------------------------------------------------------------
// Deterministic JSON log writer
// -----------------------------------------------------------------------------
export async function logLlmUsage(entry: LlmUsageLogEntry) {
  // DETERMINISZTIKUS SORREND — minden log sor ugyanúgy néz ki
  const orderedEntry = {
    timestamp: entry.timestamp,
    sessionId: entry.sessionId ?? null,
    requestId: entry.requestId,

    component: entry.component,
    model: entry.model,
    provider: entry.provider,

    promptTokens: entry.promptTokens,
    completionTokens: entry.completionTokens,
    totalTokens: entry.totalTokens,

    costUsd: entry.costUsd,
    latencyMs: entry.latencyMs,

    success: entry.success,
    errorMessage: entry.errorMessage ?? null,
  };

  const line = `[LLM_USAGE] ${JSON.stringify(orderedEntry)}\n`;

  // Konzolra írás
  console.log(line.trim());

  // Fájlba írás
  const logsDir = path.join(process.cwd(), "logs");
  const logFile = path.join(logsDir, "llm-usage.log");

  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }

  fs.appendFile(logFile, line, (err) => {
    if (err) {
      console.error("Log hiba:", err);
    }
  });
}
