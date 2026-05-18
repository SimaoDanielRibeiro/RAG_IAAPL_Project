export interface DocumentInfo {
  id: string;
  name: string;
  size_bytes: number;
}

export interface HealthResponse {
  status: string;
  documents_count: number;
  chat_model: string;
  embedding_model: string;
}

export interface ChunkInfo {
  source: string;
  page: number | null;
  score: number | null;
  snippet: string;
}

export interface ChatResponse {
  answer: string;
  confidence: "High" | "Medium" | "Low";
  sources: string[];
  pages: number[];
  citations: string[];
  chunks_used: number;
  average_score: number | null;
  queries: string[];
  retrieval_question: string;
  documents: ChunkInfo[];
  answer_mode: string;
  source_distribution: Record<string, number>;
  document_ids: string[];
}

export interface SummaryEntry {
  file_name: string;
  summary: string;
  pages: number[];
}

export interface SummaryResponse {
  summaries: SummaryEntry[];
}

export type AnswerMode = "standard" | "exhaustive";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  evidence?: ChatResponse;
  isSummary?: boolean;
  summaryData?: SummaryResponse;
  timestamp: Date;
}
