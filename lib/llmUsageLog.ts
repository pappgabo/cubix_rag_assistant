// lib/llmUsageLog.ts

import fs from "fs";
import path from "path";

// Egyetlen LLM-hívás naplózásához használt típus.
// Minden mező egy-egy fontos adatot rögzít a költségszámításhoz,
// hibakereséshez, teljesítményméréshez vagy auditáláshoz.
export type LlmUsageLogEntry = {
  timestamp: string;          
  // A hívás időpontja ISO formátumban (pl. new Date().toISOString()).

  requestId: string;          
  // Egyedi azonosító a kéréshez. Jó gyakorlat: crypto.randomUUID().

  sessionId?: string;         
  // Opcionális: chat session ID vagy eval futás ID-ja.
  // Akkor hasznos, ha több hívást szeretnél összekapcsolni.

  component: string;          
  // Annak a komponensnek a neve, amely az LLM-et hívta.
  // Példák: "chat", "rerank", "judge", "eval", "embedding" stb.

  model: string;              
  // A használt modell neve, pl. "gpt-4.1-mini", "gpt-4.1".

  provider: string;           
  // A szolgáltató neve, pl. "openai", "anthropic", "google".

  promptTokens: number;
  // A bemeneti prompt tokenjeinek száma.

  completionTokens: number;
  // A modell által generált válasz tokenjeinek száma.

  totalTokens: number;
  // promptTokens + completionTokens (könnyebb így tárolni).

  costUsd: number;
  // A hívás becsült költsége USD-ben (provider pricing alapján számolva).

  latencyMs: number;
  // Mennyi időbe telt a hívás (round-trip), ez teljesítményméréshez fontos.

  success: boolean;
  // Sikeres volt-e a hívás. Ha false, akkor az errorMessage mező kitöltött lehet.

  errorMessage?: string;
  // Opcionális hibaüzenet, ha a hívás sikertelen volt.
};


// Egyszerű árlista tokenenkénti költséggel.
// A kulcs a modell neve, az érték pedig input/output tokenár 1000 tokenre.
// Később könnyen bővíthető új modellekkel.
const MODEL_PRICES_USD_PER_1K_TOKENS: Record<
  string,
  { input: number; output: number }
> = {
  "gpt-4.1-mini": { input: 0.00015, output: 0.0006 },
  "gpt-4.1": { input: 0.005, output: 0.015 },
};


// A költség kiszámítása a modell árlistája alapján.
// promptTokens → input tokenek száma
// completionTokens → output tokenek száma
// A visszatérési érték USD-ben van, 6 tizedesre kerekítve.
export function calcCostUsd(
  model: string,
  promptTokens: number,
  completionTokens: number,
): number {
  const prices = MODEL_PRICES_USD_PER_1K_TOKENS[model];

  // Ha nincs árlista ehhez a modellhez, 0 költséget adunk vissza.
  if (!prices) return 0;

  // Tokenek ezres egységre normalizálva.
  const inputCost = (promptTokens / 1000) * prices.input;
  const outputCost = (completionTokens / 1000) * prices.output;

  // Összeg + 6 tizedesre kerekítés (pl. 0.000123 → 0.000123).
  return +(inputCost + outputCost).toFixed(6);
}


// A logoló függvény, amely egy LlmUsageLogEntry objektumot vár.
// Jelenleg két dolgot csinál:
//   1) kiírja a konzolra
//   2) hozzáfűzi egy fájlhoz (logs/llm-usage.log)
// A fájl automatikusan létrejön, ha nem létezik.
export async function logLlmUsage(entry: LlmUsageLogEntry) {
  // A log egyetlen sorban, JSON-ként kerül kiírásra.
  const line = `[LLM_USAGE] ${JSON.stringify(entry)}\n`;

  // 1) Konzolra írás (hasznos fejlesztés közben)
  console.log(line.trim());

  // 2) Fájlba írás
  // A logs könyvtár a projekt gyökerében lesz (process.cwd()) Jelen példa alapján "logs" 
  // lesz a neve a könyvtárnak és llm-usage.log a fájl neve.
  const logsDir = path.join(process.cwd(), "logs");
  const logFile = path.join(logsDir, "llm-usage.log");

  // Ha a logs mappa nem létezik, létrehozzuk.
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }

  // A log sor hozzáfűzése a fájlhoz.
  // Ha hiba történik, azt a konzolra írjuk.
  fs.appendFile(logFile, line, (err) => {
    if (err) {
      console.error("Nem sikerült az LLM logot fájlba írni:", err);
    }
  });
}
