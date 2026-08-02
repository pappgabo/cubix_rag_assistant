/** Forrás chunk a chat válaszban (RAGResponse.chunks megfelelője). */

export interface RagSource {
  docId: string;
  baseId: string;
  text: string;
  score: number;
}

export interface RagQueryResult {
  answer: string;
  sources: RagSource[];
  model: string;
}
