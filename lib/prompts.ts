import fs from "fs";
import path from "path";

const PROMPTS_DIR = path.join(process.cwd(), "prompts");

export function loadPrompt(relativePath: string): string {
  const fullPath = path.join(PROMPTS_DIR, relativePath);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`Hiányzó prompt fájl: ${fullPath}`);
  }
  return fs.readFileSync(fullPath, "utf-8").trim();
}

export function renderTemplate(
  template: string,
  values: Record<string, string>
): string {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replaceAll(`{${key}}`, value),
    template
  );
}
